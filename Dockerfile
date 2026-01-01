# Pythonのバージョン指定
FROM python:3.9-slim

# 作業ディレクトリの設定
WORKDIR /app

# 必要なツール（コンパイラ等）のインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 先にライブラリ一覧だけコピー（キャッシュ効率化のため）
COPY app/requirements.txt .

# ライブラリのインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリ本体をコピー
COPY app/ .

# 起動コマンド
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]