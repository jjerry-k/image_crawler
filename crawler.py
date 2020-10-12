# %%
import os, time, platform, argparse
import hashlib, psutil, threading, queue
from urllib.request import urlopen
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

def download_url(path, url):
    with urlopen(url) as f:
        img = f.read()
        # print(img)
        md5 = hashlib.md5()
        md5.update(img)
        name = md5.hexdigest()
        with open(os.path.join(path, f"{name}.jpg"),'wb') as h: # w - write b - binary
            h.write(img)

class Download(threading.Thread):
    
    def __init__(self, workQueue, dst, max_img):
        self.signal = True
        threading.Thread.__init__(self)
        self.workQueue = workQueue
        self.dst = dst
        self.max_img = max_img

    def stop(self):
        self.signal = False

    def run(self):
        idx = 0
        while self.signal:
            url = self.workQueue.get()
            if url is None :
                break
            download_url(self.dst, url)
            idx += 1
            if idx == self.max_img:
                break

def crawler(keyword, dst_root, mode = "headless", num_image=50):

    # Check Platform 
    if platform.system() == 'Windows':
        print('Detected OS : Windows')
        executable = './webdriver/chromedriver.exe'
    elif platform.system() == 'Linux':
        print('Detected OS : Linux')
        executable = './webdriver/chromedriver_linux'
    elif platform.system() == 'Darwin':
        print('Detected OS : Mac')
        executable = './webdriver/chromedriver_mac'

    options = webdriver.ChromeOptions()
    options.add_argument('window-size=1920x1080')
    options.add_argument("disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36")
    options.add_argument("lang=ko_KR") # 한국어!
    
    print("Start Crawling ! ")
    if mode == "headless":
        options.add_argument(mode)
    driver = webdriver.Chrome(executable, options=options)
    driver.implicitly_wait(1.5)

    driver.get(f"https://www.google.com/search?q={keyword}&source=lnms&tbm=isch")

    time.sleep(1)

    elem = driver.find_element_by_tag_name("body")

    for i in range(10):
        elem.send_keys(Keys.PAGE_DOWN)
        time.sleep(0.2)

    photo_grid_boxes = driver.find_elements(By.XPATH, '//div[@class="bRMDJf islir"]')

    links = []    
    for box in photo_grid_boxes:
        # try:
        imgs = box.find_elements(By.TAG_NAME, "img")
        for img in imgs:
            src = img.get_attribute("src")
            if str(src).startswith("data:"):
                src = img.get_attribute("data-iurl")
            if src == None: continue
            links.append(src)
    
    print(f"{len(links)} {keyword} images collected!")
    
    cpu_core_count = psutil.cpu_count(logical=True)
    print(f"Number of cores: {cpu_core_count}")
    qu  = queue.Queue()
    threads = []

    # Put whole files to queue.
    for link in links:
        qu.put(link)

    # To terminate thread, put terminate keyword on the queue.
    for _ in range(cpu_core_count):
        qu.put(None)

    # Crate thread as much as CPU core count
    for _ in range(cpu_core_count):
        threads.append(Download(qu, dst_root, num_image))

    # Start each thread
    for t in threads:
        t.start()

    # Wait thread until all processing will be finished
    for t in threads:
        t.join()

    # for idx, link in tqdm(enumerate(links)):
    #     if idx >= num_image: break
    #     download_url(dst_root, link, idx+1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", dest="keyword", type=str, default="cat", help="Keyword that you want to collect")
    parser.add_argument("--save_root", dest="save_root", type=str, default="./result", help="Path of save root directory")
    parser.add_argument("--mode", dest="mode", type=str, default="headless", help="Kind of webdriver")
    parser.add_argument("--num_image", dest="num_image", type=int, default=20, help="Image limit")
    args = parser.parse_args()

    dst_path = os.path.join(args.save_root, args.keyword)
    os.makedirs(dst_path, exist_ok=True)
    crawler(args.keyword, dst_path, args.mode, args.num_image)