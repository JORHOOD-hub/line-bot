FROM python:3.11-slim

# Ghostscript, LibreOffice, その他必要なツールをインストール
RUN apt-get update && apt-get install -y \
    ghostscript \
    libreoffice \
    poppler-utils \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 依存ライブラリをインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# 必要なディレクトリを作成
RUN mkdir -p /app/data /app/output /app/templates

# ポート公開
EXPOSE 5000

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health')"

# アプリケーション起動
CMD ["python", "main.py"]
