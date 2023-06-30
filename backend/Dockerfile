FROM python:3.10-slim

RUN apt update -y

RUN apt install -y \
        build-essential \
        cmake \
        vim \
        git \
        curl \
        wget \
        ca-certificates \
        libjpeg-dev \
        libpng-dev \
        libgl1-mesa-glx \
        libglib2.0-0

RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR "/app"

COPY . .

RUN pip3 install --no-cache-dir Flask selenium pymongo torch torchvision torchaudio timm openpyxl pandas opencv-python

CMD ["python", "backend.py"]