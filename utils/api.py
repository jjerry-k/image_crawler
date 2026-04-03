import requests
import utils


def _build_payload(test: bool) -> dict:
    return {"test": str(bool(test)).lower()}


def _build_files(bytes_data: bytes) -> dict:
    return {
        "file": (
            "crawling.xlsx",
            bytes_data,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    }


def request_crawling(bytes_data, test=False):
    response = requests.post(
        utils.build_backend_url("/request/crawl"),
        files=_build_files(bytes_data),
        data=_build_payload(test),
        timeout=utils.REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def request_crwling(bytes_data, test=False):
    return request_crawling(bytes_data, test=test)


def request_delete(test=False):
    response = requests.post(
        utils.build_backend_url("/request/delete"),
        params=_build_payload(test),
        timeout=utils.STATUS_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def request_status(test=False):
    response = requests.get(
        utils.build_backend_url("/request/status"),
        params=_build_payload(test),
        timeout=utils.STATUS_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()
