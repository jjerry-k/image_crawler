
import os
import shutil
from io import BytesIO
from queue import Queue

import time
import logging
import threading
import traceback
from datetime import datetime

import numpy as np
import pandas as pd
from PIL import Image, Image

import utils
from utils import crawler
from utils.mongo import *

NUM_WORKERS = 4

logging.basicConfig(filename = "backend.log", format='%(levelname)s :: %(asctime)s :: %(message)s', level = logging.INFO)

def crawling(date, key_class, keyword, class_path, test=False):
    print(f"=================================================================")
    print(f"=================================================================")
    print(f"=================================================================")
    print(f"Start Crawling: {class_path}, {keyword}")
    result = crawler.crawling(class_path, keyword)
    if test:
        TARGET_COLL = MONGO_DATA_TEST_COLL
    else:
        TARGET_COLL = MONGO_DATA_COLL
            
    if result:
        keyword_path = os.path.join(class_path, keyword)
        file_list = os.listdir(keyword_path)
        for file in file_list:
            src = os.path.join(keyword_path, file)
            dst = os.path.join(class_path, file)
            shutil.move(src, dst)
        
        # 키워드 폴더 삭제
        shutil.rmtree(keyword_path)
        
        update_doc(TARGET_COLL, 
                        filter={"date": date, "key_class": key_class, "keyword": keyword, "crawled": "Proceeding"}, 
                        update={"$set": {"crawled": "Success"}})
    else:
        update_doc(TARGET_COLL, 
                        filter={"date": date, "key_class": key_class, "keyword": keyword, "crawled": "Proceeding"}, 
                        update={"$set": {"crawled": "Fail"}})

class BackgroundWorker(threading.Thread):
    def __init__(self, app, test=False):
        super().__init__()
        self.app = app
        self.ROOT = utils.TEST_ROOT if test else utils.ROOT
        self.TARGET_COLL = MONGO_DATA_TEST_COLL if test else MONGO_DATA_COLL
        self.test = test
        self.workers = []
        self.queue = Queue()

        for status in ["Fail", "Proceeding", "Ready"]:
            docs = search_doc(self.TARGET_COLL, filter={"crawled": status})
            for doc in docs:
                self.queue.put(doc)
            
        for i in range(2 if self.test else NUM_WORKERS):
            worker = threading.Thread(target=self.run_worker, args=(i,))
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
        print(f"Number of workers : {len(self.workers)}")
        
    def run_worker(self, worker_num):
        while True:
            time.sleep(0.1*worker_num)
            if self.queue.qsize() == 0:
                # self.app.logger.info("No Item")
                # DB load
                pass
            else:
                item = self.queue.get()
                if item:
                    data = item["date"]
                    key_class = item["key_class"]
                    keyword = item["keyword"]
                    class_path = item["class_path"]
                    
                    update_doc(self.TARGET_COLL, 
                                filter={"date": data, "key_class": key_class, "keyword": keyword, "class_path": class_path, "crawled": "Ready"}, 
                                update={"$set": {"crawled": "Proceeding"}})
                    self.app.logger.info(f"{'Test ' if self.test else ''}Worker number: {worker_num}, Current item: {key_class}, {keyword} Start")
                    crawling(data, key_class, keyword, class_path, self.test)
                    self.app.logger.info(f"{'Test ' if self.test else ''}Worker number: {worker_num}, Current item: {key_class}, {keyword} Finish")

    def add_queue(self, item):
        db = MONGO_CLIENT[MONGO_DB][self.TARGET_COLL].count_documents(item)
        if not db:
            insert_doc(self.TARGET_COLL, item)
            self.queue.put(item)

    def delete_queue(self):
        self.app.logger.info(f"{'Test ' if self.test else ''}Queue Delete, Number of Queue: {len(self.queue.queue)}")
        
        self.queue = Queue()
        
        docs = search_doc(self.TARGET_COLL, filter={"crawled": "Ready"})
        for doc in docs:
            delete_doc(self.TARGET_COLL, filter={"crawled": "Ready"})

from flask import Flask, request
app = Flask(__name__)

worker = BackgroundWorker(app)

@app.route('/')
def root():
    return {"message": "Hello World"}

@app.route('/request/crawl', methods=["POST"])
def crawl():
    
    try:
        date = str(datetime.now().date())

        crawling_list = pd.read_excel(request.files['file'])[["class", "keyword"]]
        crawling_list = crawling_list[~crawling_list["class"].isnull()]
        
        ROOT = utils.ROOT
        target_worker = worker

        for _, (key_class, keywords) in crawling_list.iterrows():
            try:
                keywords = [keyword.strip() for keyword in keywords.split(",")]
                class_path = os.path.join(ROOT, key_class)
                for keyword in keywords:
                    item = {
                        "date": date,
                        "key_class": key_class,
                        "keyword": keyword,
                        "class_path": class_path,
                        "crawled": "Ready"
                        }           
                    target_worker.add_queue(item)
                    
            except Exception as e:
                print(f"Second Exception")
                print(traceback.format_exc())
                
        MSG = "Success"
    except Exception as e:
        print(f"First Exception")
        print(traceback.format_exc())
        MSG = "Failed"
    return {"MSG": MSG}

@app.route('/request/delete', methods=["GET"])
def delete():
    ROOT = utils.ROOT
    target_worker = worker
    target_worker.delete_queue()
    return {"MSG": "Success"}

@app.route('/request/check', methods=["GET"])
def check():
    ROOT = utils.ROOT
    target_worker = worker
    return {"MSG": list(target_worker.queue.queue)}

if __name__ == '__main__':
    app.run(host="0.0.0.0", port="5000")