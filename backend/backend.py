import mimetypes
import logging
import os
import shutil
import tempfile
import threading
import time
import traceback
import zipfile
from datetime import datetime
from queue import Empty, Queue

import pandas as pd
import pymongo
from flask import Flask, request, send_file
from pymongo.errors import DuplicateKeyError

import utils
from utils import crawler
from utils.mongo import (
    MONGO_DATA_COLL,
    MONGO_DATA_TEST_COLL,
    count_docs,
    delete_doc,
    delete_docs,
    ensure_indexes,
    find_one_doc,
    find_one_and_update_doc,
    get_collection,
    insert_doc,
    search_doc,
    update_doc,
    wait_for_mongo,
)

NUM_WORKERS = int(os.getenv("NUM_WORKERS", "4"))
WORKER_POLL_INTERVAL = float(os.getenv("WORKER_POLL_INTERVAL", "1"))
STATUSES = ("Ready", "Proceeding", "Success", "Fail")
JOB_SORT = [("date", pymongo.DESCENDING), ("key_class", pymongo.DESCENDING), ("keyword", pymongo.DESCENDING)]
JOB_FIELDS = ("date", "key_class", "keyword", "class_path")

logging.basicConfig(
    filename="backend.log",
    format="%(levelname)s :: %(asctime)s :: %(message)s",
    level=logging.INFO,
)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def parse_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def get_test_mode(req) -> bool:
    if req.args.get("test") is not None:
        return parse_bool(req.args.get("test"))
    if req.form.get("test") is not None:
        return parse_bool(req.form.get("test"))
    if req.is_json and req.get_json(silent=True):
        return parse_bool(req.get_json(silent=True).get("test"))
    return False


def normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def serialize_doc(doc):
    serialized = dict(doc)
    serialized.pop("_id", None)
    return serialized


def build_item_filter(item):
    return {
        "date": item["date"],
        "key_class": item["key_class"],
        "keyword": item["keyword"],
        "class_path": item["class_path"],
    }


def build_job_paths(root: str, key_class: str, keyword: str):
    class_directory = utils.safe_path_component(key_class, fallback="class")
    storage_directory = utils.build_keyword_directory(keyword)
    class_path = os.path.join(root, class_directory)
    storage_path = os.path.join(class_path, storage_directory)
    return class_path, storage_path, storage_directory


def get_target_collection_name(test_mode: bool) -> str:
    return MONGO_DATA_TEST_COLL if test_mode else MONGO_DATA_COLL


def get_request_value(req, key: str):
    if req.args.get(key) is not None:
        return req.args.get(key)
    if req.form.get(key) is not None:
        return req.form.get(key)
    if req.is_json and req.get_json(silent=True):
        payload = req.get_json(silent=True)
        if payload.get(key) is not None:
            return payload.get(key)
    return None


def get_request_values(req, key: str) -> list[str]:
    values = []
    values.extend(req.args.getlist(key))
    values.extend(req.form.getlist(key))

    if req.is_json and req.get_json(silent=True):
        payload = req.get_json(silent=True)
        raw_value = payload.get(key)
        if isinstance(raw_value, list):
            values.extend(raw_value)
        elif raw_value is not None:
            values.append(raw_value)

    return values


def resolve_storage_paths(item):
    storage_dir = item.get("storage_dir") or utils.build_keyword_directory(item["keyword"])
    storage_path = item.get("storage_path") or os.path.join(item["class_path"], storage_dir)
    return storage_path, storage_dir


def normalize_job_doc(doc):
    normalized = serialize_doc(doc)
    storage_path, storage_dir = resolve_storage_paths(normalized)
    normalized["storage_path"] = storage_path
    normalized["storage_dir"] = storage_dir
    return normalized


def load_job_from_request(req):
    test_mode = get_test_mode(req)
    collection_name = get_target_collection_name(test_mode)
    item_filter = {}
    missing_fields = []

    for field in JOB_FIELDS:
        value = get_request_value(req, field)
        if value in (None, ""):
            missing_fields.append(field)
        else:
            item_filter[field] = value

    if missing_fields:
        return None, collection_name, test_mode, f"missing required params: {', '.join(missing_fields)}", 400

    doc = find_one_doc(collection_name, item_filter)
    if doc is None:
        return None, collection_name, test_mode, "job not found", 404

    return normalize_job_doc(doc), collection_name, test_mode, None, 200


def touch_job(collection_name: str, item):
    update_doc(
        collection_name,
        filter=build_item_filter(item),
        update={"$set": {"updated_at": now_iso()}},
    )


def list_job_images(item):
    storage_path, _ = resolve_storage_paths(item)
    if not os.path.isdir(storage_path):
        return []

    images = []
    with os.scandir(storage_path) as entries:
        for entry in sorted(entries, key=lambda current: current.name):
            if not entry.is_file():
                continue
            mime_type, _ = mimetypes.guess_type(entry.name)
            if mime_type and not mime_type.startswith("image/"):
                continue
            stat = entry.stat()
            images.append(
                {
                    "name": entry.name,
                    "size": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                    "mime_type": mime_type or "application/octet-stream",
                }
            )
    return images


def get_image_file_path(item, file_name: str):
    if not file_name:
        raise ValueError("name is required")

    safe_name = os.path.basename(file_name)
    if safe_name != file_name:
        raise ValueError("invalid file name")

    storage_path, _ = resolve_storage_paths(item)
    file_path = os.path.join(storage_path, safe_name)
    if not os.path.isfile(file_path):
        raise FileNotFoundError("image not found")
    return file_path, safe_name


def get_requested_image_names(req) -> list[str]:
    names = []
    seen = set()
    for raw_name in get_request_values(req, "name"):
        file_name = normalize_text(raw_name)
        if not file_name:
            continue
        safe_name = os.path.basename(file_name)
        if safe_name != file_name:
            raise ValueError("invalid file name")
        if safe_name not in seen:
            names.append(safe_name)
            seen.add(safe_name)
    return names


def resolve_requested_images(item, file_names: list[str] | None = None):
    if not file_names:
        images = list_job_images(item)
        if not images:
            raise FileNotFoundError("no images available")

        storage_path, _ = resolve_storage_paths(item)
        return [
            {
                "name": image["name"],
                "path": os.path.join(storage_path, image["name"]),
            }
            for image in images
        ]

    resolved = []
    for file_name in file_names:
        file_path, safe_name = get_image_file_path(item, file_name)
        resolved.append({"name": safe_name, "path": file_path})

    if not resolved:
        raise ValueError("name is required")

    return resolved


def build_job_archive(item, file_names: list[str] | None = None):
    images = resolve_requested_images(item, file_names)

    archive_file = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
    with zipfile.ZipFile(archive_file, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for image in images:
            archive.write(image["path"], arcname=image["name"])

    archive_file.seek(0)
    suffix = "-selected" if file_names else ""
    file_name = f"{utils.safe_path_component(item['key_class'])}-{utils.safe_path_component(item['keyword'])}{suffix}.zip"
    return archive_file, file_name


def remove_job_storage(item):
    storage_path, _ = resolve_storage_paths(item)
    if os.path.isdir(storage_path):
        shutil.rmtree(storage_path)
    cleanup_empty_directory(item["class_path"])


def cleanup_empty_directory(path: str) -> None:
    try:
        if os.path.isdir(path) and not os.listdir(path):
            os.rmdir(path)
    except OSError:
        pass


def set_job_status(
    collection: str,
    item_filter: dict,
    status: str,
    error_message: str | None = None,
    extra_fields: dict | None = None,
) -> None:
    set_fields = {
        "crawled": status,
        "updated_at": now_iso(),
    }
    unset_fields = {}

    if extra_fields:
        for key, value in extra_fields.items():
            if value is None:
                unset_fields[key] = ""
            else:
                set_fields[key] = value

    if error_message is None:
        unset_fields["error_message"] = ""
    else:
        set_fields["error_message"] = error_message

    update_payload = {"$set": set_fields}
    if unset_fields:
        update_payload["$unset"] = unset_fields

    update_doc(
        collection,
        filter=item_filter,
        update=update_payload,
    )


def process_crawling(item, test=False):
    target_coll = get_target_collection_name(test)
    item_filter = build_item_filter(item)
    os.makedirs(item["class_path"], exist_ok=True)
    app.logger.info("Start Crawling: %s, %s", item["class_path"], item["keyword"])
    result = crawler.crawling(
        item["class_path"],
        item["keyword"],
        image_directory=item["storage_dir"],
    )

    if isinstance(result, bool):
        result = {
            "success": result,
            "downloaded": 0,
            "error": None if result else "크롤러가 실패를 반환했습니다.",
        }

    if result.get("success"):
        set_job_status(
            target_coll,
            item_filter,
            "Success",
            extra_fields={"downloaded_images": result.get("downloaded")},
        )
        return

    cleanup_empty_directory(item["storage_path"])
    set_job_status(
        target_coll,
        item_filter,
        "Fail",
        error_message=result.get("error") or "이미지 수집에 실패했습니다.",
        extra_fields={"downloaded_images": result.get("downloaded", 0)},
    )


class BackgroundWorker:
    def __init__(self, app, test=False):
        self.app = app
        self.root = utils.TEST_ROOT if test else utils.ROOT
        self.target_coll = MONGO_DATA_TEST_COLL if test else MONGO_DATA_COLL
        self.test = test
        self.queue = Queue()
        self.collection = get_collection(self.target_coll)
        self.workers = []

        self._restore_pending_jobs()

        worker_count = 2 if self.test else max(1, NUM_WORKERS)
        for worker_num in range(worker_count):
            worker = threading.Thread(target=self.run_worker, args=(worker_num,), daemon=True)
            worker.start()
            self.workers.append(worker)
        self.app.logger.info("%sworkers started: %s", "test " if self.test else "", len(self.workers))

    def _restore_pending_jobs(self):
        docs = search_doc(
            self.target_coll,
            filter={"crawled": {"$in": ["Ready", "Proceeding"]}},
            sort=JOB_SORT,
        )
        for doc in docs:
            if doc["crawled"] == "Proceeding":
                update_doc(
                    self.target_coll,
                    filter={"_id": doc["_id"]},
                    update={"$set": {"crawled": "Ready", "updated_at": now_iso()}},
                )
                doc["crawled"] = "Ready"
            self.queue.put(serialize_doc(doc))

    def _claim_job(self, item):
        return find_one_and_update_doc(
            self.target_coll,
            filter={**build_item_filter(item), "crawled": "Ready"},
            update={
                "$set": {
                    "crawled": "Proceeding",
                    "updated_at": now_iso(),
                },
                "$unset": {
                    "error_message": "",
                    "downloaded_images": "",
                },
            },
            return_document=pymongo.ReturnDocument.AFTER,
        )

    def run_worker(self, worker_num):
        while True:
            time.sleep(0.1 * worker_num)
            try:
                queued_item = self.queue.get(timeout=WORKER_POLL_INTERVAL)
            except Empty:
                continue

            try:
                claimed_item = self._claim_job(queued_item)
                if claimed_item is None:
                    continue

                item = serialize_doc(claimed_item)
                self.app.logger.info(
                    "%sworker=%s start class=%s keyword=%s",
                    "test " if self.test else "",
                    worker_num,
                    item["key_class"],
                    item["keyword"],
                )
                process_crawling(item, self.test)
                self.app.logger.info(
                    "%sworker=%s finish class=%s keyword=%s",
                    "test " if self.test else "",
                    worker_num,
                    item["key_class"],
                    item["keyword"],
                )
            except Exception as exc:
                self.app.logger.error(traceback.format_exc())
                set_job_status(
                    self.target_coll,
                    build_item_filter(queued_item),
                    "Fail",
                    error_message=str(exc).strip() or exc.__class__.__name__,
                )
            finally:
                self.queue.task_done()

    def add_queue(self, item):
        item_filter = build_item_filter(item)
        requeued = find_one_and_update_doc(
            self.target_coll,
            filter={**item_filter, "crawled": "Fail"},
            update={
                "$set": {
                    "crawled": "Ready",
                    "updated_at": now_iso(),
                    "storage_path": item["storage_path"],
                    "storage_dir": item["storage_dir"],
                },
                "$unset": {
                    "error_message": "",
                    "downloaded_images": "",
                },
            },
            return_document=pymongo.ReturnDocument.AFTER,
        )
        if requeued is not None:
            self.queue.put(serialize_doc(requeued))
            return True

        document = {
            **item,
            "updated_at": now_iso(),
        }
        try:
            insert_doc(self.target_coll, document)
        except DuplicateKeyError:
            return False

        self.queue.put(document)
        return True

    def delete_queue(self):
        deleted = delete_docs(self.target_coll, filter={"crawled": "Ready"})
        self.app.logger.info("%sready jobs deleted: %s", "test " if self.test else "", deleted)
        return deleted

    def get_status(self):
        docs = [serialize_doc(doc) for doc in search_doc(self.target_coll, filter={}, sort=JOB_SORT)]
        counts = {status: count_docs(self.target_coll, {"crawled": status}) for status in STATUSES}
        return {
            "counts": counts,
            "items": docs,
            "queue_size": counts["Ready"],
        }

    def get_ready_jobs(self):
        return [serialize_doc(doc) for doc in search_doc(self.target_coll, filter={"crawled": "Ready"}, sort=JOB_SORT)]


app = Flask(__name__)
workers = {}
workers_lock = threading.Lock()


def initialize_workers():
    if workers:
        return

    with workers_lock:
        if workers:
            return

        try:
            utils.ensure_data_dirs()
            wait_for_mongo()
            ensure_indexes()
            workers[False] = BackgroundWorker(app, test=False)
            workers[True] = BackgroundWorker(app, test=True)
        except Exception:
            workers.clear()
            app.logger.error("backend initialization failed\n%s", traceback.format_exc())
            raise


def get_worker(test_mode: bool) -> BackgroundWorker:
    initialize_workers()
    return workers[test_mode]


@app.route("/")
def root():
    return {
        "message": "Hello World",
        "initialized": bool(workers),
        "workers": len(workers[False].workers) if False in workers else 0,
    }


@app.route("/healthz", methods=["GET"])
def healthz():
    try:
        initialize_workers()
    except Exception as exc:
        return {"status": "error", "error": str(exc)}, 503

    return {
        "status": "ok",
        "workers": len(workers[False].workers),
    }


@app.route("/request/crawl", methods=["POST"])
def crawl():
    try:
        test_mode = get_test_mode(request)
        target_worker = get_worker(test_mode)
        date = str(datetime.now().date())
        uploaded_file = request.files.get("file")
        if uploaded_file is None:
            return {"MSG": "Failed", "error": "file is required"}, 400

        frame = pd.read_excel(uploaded_file)
        missing_columns = [column for column in ("class", "keyword") if column not in frame.columns]
        if missing_columns:
            return {
                "MSG": "Failed",
                "error": f"missing required columns: {', '.join(missing_columns)}",
            }, 400

        crawling_list = frame[["class", "keyword"]]
        root_path = utils.TEST_ROOT if test_mode else utils.ROOT
        queued = 0

        for _, row in crawling_list.iterrows():
            key_class = normalize_text(row["class"])
            keywords_value = row["keyword"]
            if not key_class or pd.isna(keywords_value):
                continue

            keywords = [normalize_text(keyword) for keyword in str(keywords_value).split(",")]
            keywords = [keyword for keyword in keywords if keyword]

            for keyword in keywords:
                class_path, storage_path, storage_dir = build_job_paths(root_path, key_class, keyword)
                item = {
                    "date": date,
                    "key_class": key_class,
                    "keyword": keyword,
                    "class_path": class_path,
                    "storage_path": storage_path,
                    "storage_dir": storage_dir,
                    "crawled": "Ready",
                }
                queued += int(target_worker.add_queue(item))

        return {"MSG": "Success", "queued": queued}
    except Exception as exc:
        app.logger.error("crawl request failed\n%s", traceback.format_exc())
        return {"MSG": "Failed", "error": str(exc)}, 500


@app.route("/request/delete", methods=["POST"])
def delete():
    try:
        target_worker = get_worker(get_test_mode(request))
        deleted = target_worker.delete_queue()
        return {"MSG": "Success", "deleted": deleted}
    except Exception as exc:
        app.logger.error("delete request failed\n%s", traceback.format_exc())
        return {"MSG": "Failed", "error": str(exc)}, 500


@app.route("/request/status", methods=["GET"])
def status():
    try:
        test_mode = get_test_mode(request)
        target_worker = get_worker(test_mode)
        status_payload = target_worker.get_status()
        status_payload["MSG"] = "Success"
        status_payload["test"] = test_mode
        return status_payload
    except Exception as exc:
        app.logger.error("status request failed\n%s", traceback.format_exc())
        return {"MSG": "Failed", "error": str(exc)}, 500


@app.route("/request/images", methods=["GET"])
def images():
    try:
        job, collection_name, test_mode, error_message, status_code = load_job_from_request(request)
        if error_message:
            return {"MSG": "Failed", "error": error_message}, status_code

        return {
            "MSG": "Success",
            "test": test_mode,
            "item": job,
            "images": list_job_images(job),
        }
    except Exception as exc:
        app.logger.error("images request failed\n%s", traceback.format_exc())
        return {"MSG": "Failed", "error": str(exc)}, 500


@app.route("/request/image", methods=["GET", "DELETE"])
def image():
    try:
        job, collection_name, _, error_message, status_code = load_job_from_request(request)
        if error_message:
            return {"MSG": "Failed", "error": error_message}, status_code

        file_names = get_requested_image_names(request)
        if not file_names:
            return {"MSG": "Failed", "error": "name is required"}, 400

        if request.method == "DELETE":
            resolved_images = resolve_requested_images(job, file_names)
            deleted_names = []
            for image_info in resolved_images:
                os.remove(image_info["path"])
                deleted_names.append(image_info["name"])
            cleanup_empty_directory(job["storage_path"])
            cleanup_empty_directory(job["class_path"])
            touch_job(collection_name, job)
            return {
                "MSG": "Success",
                "deleted": True,
                "name": deleted_names[0] if len(deleted_names) == 1 else None,
                "names": deleted_names,
                "deleted_count": len(deleted_names),
                "remaining": len(list_job_images(job)),
            }

        file_name = file_names[0]
        file_path, safe_name = get_image_file_path(job, file_name)
        mime_type = mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
        download = parse_bool(get_request_value(request, "download"))
        return send_file(
            file_path,
            mimetype=mime_type,
            as_attachment=download,
            download_name=safe_name,
            conditional=True,
        )
    except FileNotFoundError as exc:
        return {"MSG": "Failed", "error": str(exc)}, 404
    except ValueError as exc:
        return {"MSG": "Failed", "error": str(exc)}, 400
    except Exception as exc:
        app.logger.error("image request failed\n%s", traceback.format_exc())
        return {"MSG": "Failed", "error": str(exc)}, 500


@app.route("/request/download", methods=["GET"])
def download():
    try:
        job, _, _, error_message, status_code = load_job_from_request(request)
        if error_message:
            return {"MSG": "Failed", "error": error_message}, status_code

        archive_file, archive_name = build_job_archive(job, get_requested_image_names(request) or None)
        return send_file(
            archive_file,
            mimetype="application/zip",
            as_attachment=True,
            download_name=archive_name,
            conditional=True,
        )
    except FileNotFoundError as exc:
        return {"MSG": "Failed", "error": str(exc)}, 404
    except Exception as exc:
        app.logger.error("download request failed\n%s", traceback.format_exc())
        return {"MSG": "Failed", "error": str(exc)}, 500


@app.route("/request/job", methods=["DELETE"])
def delete_job():
    try:
        job, collection_name, _, error_message, status_code = load_job_from_request(request)
        if error_message:
            return {"MSG": "Failed", "error": error_message}, status_code
        if job["crawled"] == "Proceeding":
            return {"MSG": "Failed", "error": "proceeding job cannot be deleted"}, 409

        remove_job_storage(job)
        delete_doc(collection_name, build_item_filter(job))
        return {"MSG": "Success", "deleted": True}
    except Exception as exc:
        app.logger.error("job delete request failed\n%s", traceback.format_exc())
        return {"MSG": "Failed", "error": str(exc)}, 500


@app.route("/request/check", methods=["GET"])
def check():
    try:
        target_worker = get_worker(get_test_mode(request))
        return {"MSG": "Success", "items": target_worker.get_ready_jobs()}
    except Exception as exc:
        app.logger.error("check request failed\n%s", traceback.format_exc())
        return {"MSG": "Failed", "error": str(exc)}, 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
