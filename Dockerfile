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

# Try both cookie locations
COOKIES_PATHS = ["/mnt/data/cookies.txt", "cookies.txt"]

# -----------------------
# Find cookies file
# -----------------------
def get_cookies():
    for path in COOKIES_PATHS:
        if os.path.exists(path):
            logging.info(f"🍪 Using cookies: {path}")
            return path
    return None

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

        cookies = get_cookies()
        if cookies:
            command += ["--cookies", cookies]

        command += ["-g", youtube_url]

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0:
            url = result.stdout.strip()
            if url:
                logging.info("✅ Stream URL ready")
                return url

        logging.error(result.stderr)
        return None

    except Exception:
        logging.exception("yt-dlp error")
        return None

# -----------------------
# Stream generator
# -----------------------
def generate(youtube_url):
    while True:
        stream_url = get_audio_url(youtube_url)

        if not stream_url:
            logging.warning("Retrying...")
            time.sleep(3)
            continue

        process = subprocess.Popen(
            [
                "ffmpeg",
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "10",
                "-headers", "User-Agent: Mozilla/5.0",
                "-i", stream_url,
                "-vn",
                "-ac", "1",
                "-b:a", "48k",
                "-f", "mp3",
                "-"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        try:
            for chunk in iter(lambda: process.stdout.read(4096), b""):
                if chunk:
                    yield chunk
        except GeneratorExit:
            process.terminate()
            process.wait()
            break
        except Exception as e:
            logging.error(e)

        process.terminate()
        process.wait()
        time.sleep(2)

# -----------------------
# Home page (input form)
# -----------------------
@app.route("/", methods=["GET", "POST"])
def home():
    html = """
    <html>
    <head>
        <title>🎵 YouTube Radio</title>
        <style>
            body { font-family: Arial; padding: 20px; }
            input { width: 80%; padding: 10px; }
            button { padding: 10px; }
        </style>
    </head>
    <body>
        <h3>🎵 YouTube Live → Radio</h3>
        <form method="POST">
            <input type="text" name="url" placeholder="Paste YouTube live URL" required>
            <button type="submit">Play</button>
        </form>
    </body>
    </html>
    """

    if request.method == "POST":
        url = request.form.get("url")
        return f"<a href='/play?url={url}'>▶️ Click to Play Stream</a>"

    return render_template_string(html)

# -----------------------
# Play route
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
