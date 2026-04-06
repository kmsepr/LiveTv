import subprocess
import time
import logging
from flask import Flask, Response

# -----------------------
# Config
# -----------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
app = Flask(__name__)

# 👉 Use ONE reliable test channel first
YOUTUBE_URL = "https://www.youtube.com/@AlJazeeraEnglish/live"

# -----------------------
# Get audio URL (FIXED)
# -----------------------
def get_audio_url():
    try:
        command = [
            "yt-dlp",
            "-f", "bestaudio/best",
            "--no-warnings",
            "--extractor-args", "youtube:player_client=android",
            "--user-agent", "Mozilla/5.0",
            "-g",
            YOUTUBE_URL
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0:
            url = result.stdout.strip()
            if url:
                logging.info(f"✅ Got stream URL")
                return url

        logging.error(f"yt-dlp failed: {result.stderr.strip()}")
        return None

    except Exception:
        logging.exception("Exception in yt-dlp")
        return None

# -----------------------
# Stream generator
# -----------------------
def generate():
    while True:
        url = get_audio_url()

        if not url:
            logging.warning("⚠️ No stream URL, retrying...")
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

        logging.info("🎵 Streaming started")

        try:
            for chunk in iter(lambda: process.stdout.read(4096), b""):
                if chunk:
                    yield chunk
        except GeneratorExit:
            logging.info("❌ Client disconnected")
            process.terminate()
            process.wait()
            break
        except Exception as e:
            logging.error(f"Stream error: {e}")

        logging.warning("⚠️ Restarting stream...")
        process.terminate()
        process.wait()
        time.sleep(2)

# -----------------------
# Routes
# -----------------------
@app.route("/")
def home():
    return "🎵 YouTube Live Radio Running"

@app.route("/radio")
def radio():
    return Response(generate(), mimetype="audio/mpeg")

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
