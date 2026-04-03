import hashlib
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO

from PIL import Image, UnidentifiedImageError
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import utils

LOGGER = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}
FORMAT_EXTENSIONS = {
    "BMP": ".bmp",
    "GIF": ".gif",
    "JPEG": ".jpg",
    "PNG": ".png",
    "TIFF": ".tiff",
    "WEBP": ".webp",
}
BING_IMAGE_SCRIPT = """
const results = [];
const pushValue = (value) => {
  if (!value || typeof value !== "string") {
    return;
  }
  const trimmed = value.trim();
  if (trimmed) {
    results.push(trimmed);
  }
};

document.querySelectorAll("a.iusc").forEach((node) => {
  const meta = node.getAttribute("m");
  if (!meta) {
    return;
  }
  try {
    const parsed = JSON.parse(meta);
    pushValue(parsed.murl);
    pushValue(parsed.turl);
  } catch (error) {
  }
});

document.querySelectorAll("img.mimg").forEach((node) => {
  pushValue(node.getAttribute("src"));
  pushValue(node.getAttribute("data-src"));
  pushValue(node.getAttribute("data-src-hq"));
});

return results;
"""
MURL_PATTERN = re.compile(r'"murl":"(.*?)"')


def _build_result(success: bool, downloaded: int = 0, error: str | None = None):
    return {
        "success": success,
        "downloaded": downloaded,
        "error": error,
    }


def _build_driver():
    options = Options()
    options.binary_location = utils.CHROME_BINARY
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1600,2400")
    options.add_argument("--lang=en-US")
    options.add_argument("--blink-settings=imagesEnabled=false")

    service = Service(executable_path=utils.CHROMEDRIVER)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(utils.CRAWLER_PAGE_LOAD_TIMEOUT)
    return driver


def _normalize_candidate_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("data:"):
        return None
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None
    return url


def _click_show_more(driver) -> bool:
    for selector in ("a.btn_seemore", "input.btn_seemore", ".btn_seemore a"):
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, selector)
            for button in buttons:
                if button.is_displayed():
                    driver.execute_script("arguments[0].click();", button)
                    return True
        except WebDriverException:
            continue
    return False


def _collect_image_urls(driver, keyword: str, limit: int) -> tuple[list[str], str]:
    search_url = (
        "https://www.bing.com/images/search?"
        f"q={urllib.parse.quote_plus(keyword)}&form=HDRSC2&first=1"
    )
    driver.get(search_url)

    wait = WebDriverWait(driver, utils.CRAWLER_PAGE_LOAD_TIMEOUT)
    wait.until(lambda current_driver: current_driver.execute_script("return document.readyState") == "complete")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
    time.sleep(utils.CRAWLER_SCROLL_DELAY_SECONDS)

    unique_urls = []
    seen = set()
    target_candidates = max(limit * 4, limit + 20)
    stagnant_rounds = 0

    for _ in range(utils.CRAWLER_SCROLL_LIMIT):
        try:
            candidate_values = driver.execute_script(BING_IMAGE_SCRIPT) or []
        except WebDriverException:
            candidate_values = []

        if not candidate_values:
            candidate_values = [
                bytes(match, "utf-8").decode("unicode_escape")
                for match in MURL_PATTERN.findall(driver.page_source)
            ]

        added_this_round = 0
        for value in candidate_values:
            normalized = _normalize_candidate_url(value)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_urls.append(normalized)
            added_this_round += 1
            if len(unique_urls) >= target_candidates:
                return unique_urls, search_url

        if added_this_round == 0:
            stagnant_rounds += 1
        else:
            stagnant_rounds = 0

        if stagnant_rounds >= 2 and len(unique_urls) >= max(limit, 10):
            break

        _click_show_more(driver)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(utils.CRAWLER_SCROLL_DELAY_SECONDS)

    return unique_urls, search_url


def _guess_extension(image_format: str | None, content_type: str | None, url: str) -> str:
    if image_format:
        mapped = FORMAT_EXTENSIONS.get(image_format.upper())
        if mapped:
            return mapped

    if content_type:
        content_type = content_type.split(";", 1)[0].strip().lower()
        if content_type == "image/jpeg":
            return ".jpg"
        if content_type.startswith("image/"):
            extension = content_type.split("/", 1)[1]
            if extension == "svg+xml":
                return ".svg"
            return f".{extension}"

    path_extension = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower()
    return path_extension or ".jpg"


def _validate_image(data: bytes) -> tuple[str | None, tuple[int, int] | None]:
    try:
        with Image.open(BytesIO(data)) as image:
            image_format = image.format
            size = image.size
        return image_format, size
    except UnidentifiedImageError:
        return None, None


def _download_image(url: str, destination_dir: str, index: int, referer: str) -> bool:
    headers = {**DEFAULT_HEADERS, "Referer": referer}
    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=utils.CRAWLER_DOWNLOAD_TIMEOUT) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read()
    except Exception as exc:
        LOGGER.debug("failed to download %s: %s", url, exc)
        return False

    if len(data) < utils.CRAWLER_MIN_BYTES:
        return False

    image_format, image_size = _validate_image(data)
    if image_format is None or image_size is None:
        return False

    extension = _guess_extension(image_format, content_type, url)
    if extension == ".svg":
        return False

    digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
    file_path = os.path.join(destination_dir, f"{index:04d}-{digest}{extension}")
    with open(file_path, "wb") as output_file:
        output_file.write(data)
    return True


def crawling(root: str, keyword: str, image_directory: str | None = None):
    image_directory = image_directory or keyword
    keyword_path = os.path.join(root, image_directory)
    os.makedirs(keyword_path, exist_ok=True)

    driver = None
    downloaded = 0
    try:
        driver = _build_driver()
        candidate_urls, search_url = _collect_image_urls(driver, keyword, utils.CRAWLER_LIMIT)
        if not candidate_urls:
            LOGGER.warning("no candidate image urls found for keyword=%s", keyword)
            return _build_result(False, error="검색 결과에서 이미지 URL을 찾지 못했습니다.")

        for candidate_url in candidate_urls:
            if _download_image(candidate_url, keyword_path, downloaded + 1, search_url):
                downloaded += 1
            if downloaded >= utils.CRAWLER_LIMIT:
                break

        if downloaded == 0:
            LOGGER.warning("no files downloaded for keyword=%s", keyword)
            return _build_result(False, error="유효한 이미지를 다운로드하지 못했습니다.")

        LOGGER.info("downloaded %s images for keyword=%s", downloaded, keyword)
        return _build_result(True, downloaded=downloaded)
    except TimeoutException:
        LOGGER.exception("crawler timed out for keyword=%s", keyword)
        return _build_result(False, downloaded=downloaded, error="크롤러 실행 시간이 초과되었습니다.")
    except Exception as exc:
        LOGGER.exception("crawling failed for keyword=%s", keyword)
        message = str(exc).strip() or exc.__class__.__name__
        return _build_result(False, downloaded=downloaded, error=message)
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                LOGGER.debug("failed to close browser for keyword=%s", keyword)
