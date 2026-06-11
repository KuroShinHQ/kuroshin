# Scraper Paketi — Docker Image
# Kullanım:
#   docker build -t scraper-paket .
#   docker run --rm -v $(pwd)/cikti:/app/cikti scraper-paket
#
# Cookie ile:
#   docker run --rm \
#     -v $(pwd)/cookies.json:/app/cookies.json \
#     -v $(pwd)/cikti:/app/cikti \
#     scraper-paket

FROM python:3.11-slim

WORKDIR /app

# Sistem bağımlılıkları (curl_cffi için)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libssl-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıkları
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyaları
COPY scraper_paketi/ ./scraper_paketi/
COPY run.py .
COPY config.yaml .

# Playwright istiyorsanız (JS-render için) aşağıdaki satırları açın:
# RUN pip install playwright && playwright install chromium --with-deps

# Çıktı klasörü
RUN mkdir -p /app/cikti

# config.yaml'daki output.file'ı /app/cikti/sonuclar.csv yapın
# veya -v ile dışarıdan bağlayın

CMD ["python", "run.py", "--config", "config.yaml"]
