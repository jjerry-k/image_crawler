# %%
import os, time, urllib3, platform, argparse
from pprint import pprint
from bs4 import BeautifulSoup
from selenium import webdriver

def crawler(keyword, dst_root, mode = "headless"):

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
    if mode == "headless":
        options.add_argument(mode)
    driver = webdriver.Chrome(executable, chrome_options=options)
    driver.implicitly_wait(1.5)

    driver.get(f"https://www.google.com/search?q={keyword}&source=lnms&tbm=isch")

    time.sleep(1)

    elem = driver.find_element_by_tag_name("body")

    print(elem)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", dest="keyword", type=str, default="cat", help="Keyword that you want to collect")
    parser.add_argument("--save_root", dest="save_root", type=str, default="./result", help="Path of save root directory")
    parser.add_argument("--mode", dest="mode", type=str, default="noneP", help="Kind of webdriver")
    args = parser.parse_args()

    dst_path = os.path.join(args.save_root, args.keyword)
    os.makedirs(dst_path, exist_ok=True)
    crawler(args.keyword, dst_path, args.mode)

# %%
