import os
from utils.google_images_download import google_images_download

def crawling(root: str, keyword: str):
    try:
        class_path = os.path.join(root, keyword)
        os.makedirs(class_path, exist_ok=True)
        response = google_images_download.googleimagesdownload()
        response.download({"keywords":keyword, "limit":100, "output_directory":root, "no_numbering": True, "silent_mode": True, "chromedriver": "C://Users//doinglab//Documents//Projects//utils//google_images_download//chromedriver.exe"})
        return True
    except:
        return False