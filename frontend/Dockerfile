FROM python:3.10-slim

RUN apt update -y

RUN apt install -y git

RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR "/app"

COPY . .

RUN pip3 install --no-cache-dir streamlit pymongo openpyxl pandas

CMD ["streamlit", "run", "Crawling.py", "--server.port", "8501"]