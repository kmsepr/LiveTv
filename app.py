import subprocess
import time
import logging
import os
from flask import Flask, Response, request, render_template_string

# -----------------------
# Config
# -----------------------
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

COOKIES_FILE = "/mnt/data/cookies.txt"

# -----------------------
# Get Audio URL (IMPROVED)
# -----------------------
def get_audio_url(youtube_url):
    try:
        command = [
            "yt-dlp",
            "-f", "bestaudio",
            "--no-playlist",
            "--no-warnings",

            # 🔥 VERY IMPORTANT FIXES
            "--extractor-args", "youtube:player_client=android,web",
            "--sleep-requests", "2",
            "--sleep-interval", "2",
            "--max-sleep-interval", "5",

            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",

            "-g",
            youtube_url
        ]

        if os.path.exists(COOKIES_FILE):
            logging.info(f"🍪 Using cookies: {COOKIES_FILE}")
            command += ["--cookies", COOKIES_FILE]

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0:
            url = result.stdout.strip().split("\n")[0]
            if url:
                logging.info("✅ Stream URL ready")
                return url

        logging.error(result.stderr)
        return None

    except Exception:
        logging.exception("yt-dlp failed")
        return None


# -----------------------
# Stream Generator (SAFE LOOP)
# -----------------------
def generate(youtube_url):
    last_url = None

    while True:
        # 🔥 Don't spam yt-dlp repeatedly
        if not last_url:
            last_url = get_audio_url(youtube_url)

        if not last_url:
            logging.warning("⚠️ No stream URL, retry after delay...")
            time.sleep(15)   # IMPORTANT: avoid rate limit
            continue

        process = subprocess.Popen(
            [
                "ffmpeg",
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "10",

                "-headers", "User-Agent: Mozilla/5.0\r\n",
                "-i", last_url,

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
            logging.error(e)

        # 🔄 Refresh URL after stream break
        logging.warning("🔄 Refreshing stream URL...")
        process.terminate()
        process.wait()

        last_url = None
        time.sleep(5)


# -----------------------
# Home Page
# -----------------------
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        url = request.form.get("url")

        return f"""
        <html>
        <body style="text-align:center;">
            <h3>▶️ Stream Ready</h3>
            <audio controls autoplay>
                <source src="/play?url={url}" type="audio/mpeg">
            </audio>
            <br><br>
            <a href="/">⬅ Back</a>
        </body>
        </html>
        """

    return render_template_string("""
    <html>
    <head>
        <title>YouTube → Radio</title>
        <style>
            body { font-family: Arial; padding: 30px; text-align: center; }
            input { width: 80%; padding: 10px; margin: 10px; }
            button { padding: 10px 20px; }
        </style>
    </head>
    <body>
        <h2>🎵 YouTube Live → Radio</h2>
        <form method="POST">
            <input type="text" name="url" placeholder="Paste YouTube live URL" required>
            <br>
            <button type="submit">Play</button>
        </form>
    </body>
    </html>
    """)


# -----------------------
# Stream Route
# -----------------------
@app.route("/play")
def play():
    youtube_url = request.args.get("url")

    if not youtube_url:
        return "No URL provided"

    return Response(generate(youtube_url), mimetype="audio/mpeg")


# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
