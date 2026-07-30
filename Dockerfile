FROM python:3.11-slim

# Install only ffmpeg. That's all we need
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest
COPY..

# Koyeb sets $PORT automatically. Use it
CMD gunicorn --workers 1 --threads 4 --timeout 0 -b 0.0.0.0:$PORT app:app
