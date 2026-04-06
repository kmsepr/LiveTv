import subprocess
import time
import threading
import os
import logging
from flask import Flask, Response, render_template_string

# -----------------------
# Configure logging
# -----------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
app = Flask(__name__)

# -----------------------
# YouTube Live Streams
# -----------------------
YOUTUBE_STREAMS = {
    "media_one": "https://www.youtube.com/@MediaoneTVLive/live",
    "shajahan_rahmani": "https://www.youtube.com/@ShajahanRahmaniOfficial/live",
    "qsc_mukkam": "https://www.youtube.com/c/quranstudycentremukkam/live",
    "valiyudheen_faizy": "https://www.youtube.com/@voiceofvaliyudheenfaizy600/live",
    "skicr_tv": "https://www.youtube.com/@SKICRTV/live",
    "yaqeen_institute": "https://www.youtube.com/@yaqeeninstituteofficial/live",
    "bayyinah_tv": "https://www.youtube.com/@bayyinah/live",
    "eft_guru": "https://www.youtube.com/@EFTGuru-ql8dk/live",
    "unacademy_ias": "https://www.youtube.com/@UnacademyIASEnglish/live",
    "studyiq_hindi": "https://www.youtube.com/@StudyIQEducationLtd/live",
    "aljazeera_arabic": "https://www.youtube.com/@aljazeera/live",
    "aljazeera_english": "https://www.youtube.com/@AlJazeeraEnglish/live",
    "entri_degree": "https://www.youtube.com/@EntriDegreeLevelExams/live",
    "xylem_psc": "https://www.youtube.com/@XylemPSC/live",
    "xylem_sslc": "https://www.youtube.com/@XylemSSLC2023/live",
    "entri_app": "https://www.youtube.com/@entriapp/live",
    "entri_ias": "https://www.youtube.com/@EntriIAS/live",
    "studyiq_english": "https://www.youtube.com/@studyiqiasenglish/live",
    "voice_rahmani": "https://www.youtube.com/@voiceofrahmaniyya5828/live",
}

# -----------------------
# Cache
# -----------------------
CACHE = {}
COOKIES_FILE = "/mnt/data/cookies.txt"

# -----------------------
# Get direct audio URL
# -----------------------
def get_youtube_audio_url(youtube_url: str):
    try:
        command = ["yt-dlp", "-f", "bestaudio", "-g", youtube_url]

        if os.path.exists(COOKIES_FILE):
            command.insert(1, "--cookies")
            command.insert(2, COOKIES_FILE)

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0:
            url = result.stdout.strip()
            if url:
                return url

        logging.error(f"yt-dlp error: {result.stderr.strip()}")
        return None

    except Exception:
        logging.exception("Error extracting YouTube URL")
        return None

# -----------------------
# Refresh URLs (every 60s)
# -----------------------
def refresh_stream_urls():
    while True:
        logging.info("🔄 Refreshing stream URLs...")
        for name, url in YOUTUBE_STREAMS.items():
            direct_url = get_youtube_audio_url(url)
            if direct_url:
                CACHE[name] = direct_url
                logging.info(f"✅ {name} updated")
            else:
                logging.warning(f"❌ {name} unavailable")
        time.sleep(60)

threading.Thread(target=refresh_stream_urls, daemon=True).start()

# -----------------------
# Stream generator
# -----------------------
def generate_stream(station_name: str):
    while True:
        url = CACHE.get(station_name)

        if not url:
            logging.warning(f"No URL for {station_name}, retrying...")
            time.sleep(2)
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

        logging.info(f"🎵 Streaming {station_name}")

        try:
            for chunk in iter(lambda: process.stdout.read(4096), b""):
                if chunk:
                    yield chunk
        except GeneratorExit:
            logging.info(f"❌ Client disconnected: {station_name}")
            process.terminate()
            process.wait()
            break
        except Exception as e:
            logging.error(f"Stream error: {e}")

        logging.warning(f"⚠️ Restarting {station_name}...")
        process.terminate()
        process.wait()
        time.sleep(3)

# -----------------------
# Routes
# -----------------------
@app.route("/<station_name>")
def stream(station_name):
    if station_name not in YOUTUBE_STREAMS:
        return "Station not found", 404
    return Response(generate_stream(station_name), mimetype="audio/mpeg")

@app.route("/")
def index():
    html = """
    <html>
    <head>
    <title>🎵 Live Audio Radio</title>
    <style>
    body { font-family: sans-serif; padding: 10px; }
    a { display:block; margin:5px 0; font-weight:bold; color:blue; }
    </style>
    </head>
    <body>
    <h3>🎵 Live Streams</h3>
    """

    for i, name in enumerate(sorted(YOUTUBE_STREAMS.keys()), 1):
        display = name.replace("_", " ").title()
        html += f"<a href='/{name}'>{i}. {display}</a>"

    html += "</body></html>"
    return render_template_string(html)

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
