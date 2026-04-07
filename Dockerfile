FROM python:3.11-slim

# -----------------------------
# Environment (important)
# -----------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# -----------------------------
# System dependencies
# -----------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    git \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# -----------------------------
# Working directory
# -----------------------------
WORKDIR /app

# -----------------------------
# Python dependencies
# -----------------------------
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        flask \
        requests \
        yt-dlp \
        gunicorn

# -----------------------------
# Application files
# -----------------------------
COPY . /app

# -----------------------------
# Cookies mount location
# (Koyeb / Docker volume)
# -----------------------------
RUN mkdir -p /mnt/data

# -----------------------------
# Expose port
# -----------------------------
EXPOSE 8000

# -----------------------------
# Start server
# IMPORTANT: 1 worker only (YouTube!)
# -----------------------------
CMD ["gunicorn", "-w", "1", "--threads", "8", "-b", "0.0.0.0:8000", "app:app"]
