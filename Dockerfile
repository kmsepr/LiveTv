# Use lightweight Python image
FROM python:3.11-slim

# Install system dependencies (FFmpeg + curl)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port
EXPOSE 8000

# Run using Gunicorn (better than Flask dev server)
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8000", "app:app"]
