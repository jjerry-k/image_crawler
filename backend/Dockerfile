FROM python:3.10-slim

RUN apt update -y && apt install -y --no-install-recommends \
        ca-certificates \
        chromium \
        chromium-driver \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR "/app"

ENV PYTHONUNBUFFERED=1
ENV CHROMEDRIVER=/usr/bin/chromedriver
ENV CHROME_BINARY=/usr/bin/chromium
ENV CRAWLING_ROOT=/Data/Crawling
ENV CRAWLING_TEST_ROOT=/Data/Crawling/_test

COPY . .

RUN pip3 install --no-cache-dir Flask selenium "pymongo==3.13.0" openpyxl pandas pillow six

CMD ["python", "backend.py"]
