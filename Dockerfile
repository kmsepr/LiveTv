FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y \
    ffmpeg \
    nodejs \
    npm

RUN node -v
RUN npm -v

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD gunicorn --workers 1 --threads 4 --timeout 0 -b 0.0.0.0:$PORT app:app
