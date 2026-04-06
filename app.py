import subprocess
import time
import threading
import logging
import os
from flask import Flask, Response, render_template_string

# -----------------------
# Config
# -----------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
app = Flask(__name__)

COOKIES_FILE = "cookies.txt"

# -----------------------
# Channels (use reliable ones first)
# -----------------------
YOUTUBE_STREAMS = {
    "media_one": "https://www.youtube.com/@MediaoneTVLive/live",
    "aljazeera_english": "https://www.youtube.com/@AlJazeeraEnglish/live",
    "qsc_mukkam": "https://www.youtube.com/c/quranstudycentremukkam/live",
    "shajahan_rahmani": "https://www.youtube.com/@ShajahanRahmaniOfficial/live",
}

# -----------------------
# Cache
# -----------------------
CACHE = {}

# -----------------------
# Get audio URL
# -----------------------
def get_audio_url(youtube_url):
    try:
        command = [
            "yt-dlp",
            "-f", "bestaudio/best",
            "--no-warnings",
            "--extractor-args", "youtube:player_client=android",
            "--user-agent", "Mozilla/5.0",
        ]

        if os.path.exists(COOKIES_FILE):
            command += ["--cookies", COOKIES_FILE]
            logging.info("🍪 Using cookies")

        command += ["-g", youtube_url]

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0:
            url = result.stdout.strip()
            if url:
                return url

        logging.error(f"yt-dlp failed: {result.stderr.strip()}")
        return None

    except Exception:
        logging.exception("yt-dlp error")
        return None

# -----------------------
# Refresh URLs
# -----------------------
def refresh_streams():
    while True:
        logging.info("🔄 Refreshing streams...")
        for name, url in YOUTUBE_STREAMS.items():
            direct = get_audio_url(url)
            if direct:
                CACHE[name] = direct
                logging.info(f"✅ {name} ready")
            else:
                CACHE[name] = None
                logging.warning(f"❌ {name} unavailable")
        time.sleep(60)

threading.Thread(target=refresh_streams, daemon=True).start()

# -----------------------
# Stream generator
# -----------------------
def generate(name):
    while True:
        url = CACHE.get(name)

        if not url:
            logging.warning(f"No stream for {name}, retrying...")
            time.sleep(3)
            continue

        process = subprocess.Popen(
            [
                "ffmpeg",
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "10",
                "-headers", "User-Agent: Mozilla/5.0",
                "-i", url,
                "-vn",
                "-ac", "1",
                "-b:a", "48k",
                "-f", "mp3",
                "-"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        logging.info(f"🎵 Streaming {name}")

        try:
            for chunk in iter(lambda: process.stdout.read(4096), b""):
                if chunk:
                    yield chunk
        except GeneratorExit:
            process.terminate()
            process.wait()
            break
        except Exception as e:
            logging.error(f"Stream error: {e}")

        logging.warning(f"Restarting {name}...")
        process.terminate()
        process.wait()
        time.sleep(2)

# -----------------------
# Routes
# -----------------------
@app.route("/")
def home():
    html = """
    <html>
    <head>
        <title>🎵 Live Radio</title>
        <style>
            body { font-family: Arial; padding: 15px; }
            a { display:block; margin:8px 0; font-weight:bold; color:blue; }
            .offline { color:gray; }
        </style>
    </head>
    <body>
        <h3>🎵 Live Channels</h3>
    """

    for name in YOUTUBE_STREAMS:
        display = name.replace("_", " ").title()
        if CACHE.get(name):
            html += f"<a href='/{name}'>{display} ▶️</a>"
        else:
            html += f"<span class='offline'>{display} (offline)</span><br>"

    html += "</body></html>"
    return render_template_string(html)

@app.route("/<name>")
def stream(name):
    if name not in YOUTUBE_STREAMS:
        return "Channel not found", 404
    return Response(generate(name), mimetype="audio/mpeg")

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
