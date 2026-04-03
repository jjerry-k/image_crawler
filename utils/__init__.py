import hashlib
import os
import re

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://backend:5000").rstrip("/")
ROOT = os.getenv("CRAWLING_ROOT", "/Data/Crawling")
TEST_ROOT = os.getenv("CRAWLING_TEST_ROOT", os.path.join(ROOT, "_test"))
CHROMEDRIVER = os.getenv("CHROMEDRIVER", "/usr/bin/chromedriver")
CHROME_BINARY = os.getenv("CHROME_BINARY", "/usr/bin/chromium")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30"))
STATUS_TIMEOUT = float(os.getenv("STATUS_TIMEOUT", "10"))
AUTO_REFRESH_SECONDS = int(os.getenv("AUTO_REFRESH_SECONDS", "60"))
CRAWLER_LIMIT = int(os.getenv("CRAWLER_LIMIT", "100"))
CRAWLER_SCROLL_LIMIT = int(os.getenv("CRAWLER_SCROLL_LIMIT", "12"))
CRAWLER_PAGE_LOAD_TIMEOUT = float(os.getenv("CRAWLER_PAGE_LOAD_TIMEOUT", "20"))
CRAWLER_SCROLL_DELAY_SECONDS = float(os.getenv("CRAWLER_SCROLL_DELAY_SECONDS", "1.5"))
CRAWLER_DOWNLOAD_TIMEOUT = float(os.getenv("CRAWLER_DOWNLOAD_TIMEOUT", "20"))
CRAWLER_MIN_BYTES = int(os.getenv("CRAWLER_MIN_BYTES", "2048"))
SAFE_PATH_PATTERN = re.compile(r"[^\w.-]+", re.UNICODE)


def build_backend_url(path: str) -> str:
    return f"{BACKEND_BASE_URL}/{path.lstrip('/')}"


def ensure_data_dirs() -> None:
    os.makedirs(ROOT, exist_ok=True)
    os.makedirs(TEST_ROOT, exist_ok=True)


def safe_path_component(value: str, fallback: str = "item", max_length: int = 48) -> str:
    normalized = str(value).strip()
    normalized = normalized.replace(os.sep, "_")
    if os.altsep:
        normalized = normalized.replace(os.altsep, "_")
    normalized = SAFE_PATH_PATTERN.sub("_", normalized).strip("._-")
    normalized = normalized[:max_length].rstrip("._-")
    return normalized or fallback


def build_keyword_directory(keyword: str) -> str:
    safe_keyword = safe_path_component(keyword, fallback="keyword")
    digest = convert_hash(str(keyword).encode("utf-8"))[:8]
    return f"{safe_keyword}-{digest}"


def convert_hash(file):
    if not isinstance(file, bytes):
        with open(file, "rb") as f:
            file = f.read()

    md5 = hashlib.md5()
    md5.update(file)
    return md5.hexdigest()
