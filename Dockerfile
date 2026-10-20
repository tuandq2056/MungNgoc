FROM python:3.11-slim

# Cài đặt ffmpeg và curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    bzip2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cài đặt python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Cài đặt package ở chế độ editable
RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1
ENV EXTRACT_SRT_CACHE_DIR=/app/.cache/extract_srt_from_video

ENTRYPOINT ["extract-srt"]
CMD ["/app/sample", "-m", "all"]
