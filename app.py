import os
import subprocess
import threading
from flask import Flask, Response, render_template_string, request

app = Flask(__name__)

# =========================================================
# CONFIG
# =========================================================

COOKIES_FILE = "/mnt/data/cookies.txt"

STREAMS = {
    "media_one": "https://www.youtube.com/@mediaoneTVlive/live",
    # add more here: "name": "youtube_live_url"
}

# =========================================================
# LOGGING
# =========================================================

def log(prefix, message):
    print(f"[{prefix}] {message}", flush=True)

# =========================================================
# HTML TEMPLATE FOR HOME PAGE
# =========================================================

HOME_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>YouTube Audio Stream Server</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: system-ui, sans-serif; background: #0f1117; color: #e6e6e6; margin: 0; padding: 20px; }
        .container { max-width: 700px; margin: auto; }
        h1 { text-align: center; color: #4ade80; }
        .card { background: #1a1d24; padding: 16px; border-radius: 12px; margin: 12px 0; border: 1px solid #2a2f3a; }
        .card a { color: #60a5fa; text-decoration: none; font-weight: 600; font-size: 18px; }
        .card a:hover { text-decoration: underline; }
        .url { font-size: 12px; color: #9ca3af; word-break: break-all; }
        .footer { text-align: center; margin-top: 30px; font-size: 12px; color: #6b7280; }
        .badge { background: #ef4444; color: white; padding: 2px 8px; border-radius: 6px; font-size: 11px; margin-left: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔴 YouTube Audio Stream Server</h1>
        <p style="text-align:center; color:#9ca3af;">Click to start listening</p>
        
        {% for name, url in streams.items() %}
        <div class="card">
            <a href="/{{ name }}" target="_blank">{{ name.replace('_', ' ').title() }} <span class="badge">LIVE</span></a>
            <div class="url">Source: {{ url }}</div>
            <div style="margin-top:8px;">
                <b>Direct Stream:</b> <a href="/{{ name }}">{{ request.host_url }}{{ name }}</a>
            </div>
        </div>
        {% endfor %}
        
        <div class="footer">
            Cookies: {{ cookies_status }}
        </div>
    </div>
</body>
</html>
"""

# =========================================================
# STREAM FUNCTION
# =========================================================

def generate_stream(url):
    log("SYSTEM", "=" * 50)
    log("SYSTEM", "NEW STREAM SESSION")
    log("SYSTEM", f"URL = {url}")
    log("SYSTEM", f"Cookies file exists = {os.path.exists(COOKIES_FILE)}")

    yt_cmd = [
        "yt-dlp",
        "-v",
        "-f", "bestaudio[abr<=96]/bestaudio/best",
        "-o", "-",
        "--no-warnings",
        "--live-from-start",
        "--retries", "10",
        "--fragment-retries", "10",
        "--extractor-args", "youtube:player_client=android",
        "--cookies", COOKIES_FILE,
        url
    ]

    ffmpeg_cmd = [
        "ffmpeg",
        "-loglevel", "info",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",
        "-i", "pipe:0",
        "-vn",
        "-ac", "1",
        "-ar", "22050",
        "-b:a", "40k",
        "-f", "mp3",
        "-"
    ]

    yt_process = subprocess.Popen(yt_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
    ffmpeg_process = subprocess.Popen(ffmpeg_cmd, stdin=yt_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)

    def log_yt():
        for line in yt_process.stderr:
            try: log("YT-DLP", line.decode(errors="ignore").rstrip())
            except: pass
    def log_ffmpeg():
        for line in ffmpeg_process.stderr:
            try: log("FFMPEG", line.decode(errors="ignore").rstrip())
            except: pass
    threading.Thread(target=log_yt, daemon=True).start()
    threading.Thread(target=log_ffmpeg, daemon=True).start()

    try:
        while True:
            chunk = ffmpeg_process.stdout.read(4096)
            if not chunk: break
            yield chunk
    finally:
        try: yt_process.kill()
        except: pass
        try: ffmpeg_process.kill()
        except: pass
        log("SYSTEM", "SESSION ENDED")

# =========================================================
# ROUTES
# =========================================================

@app.route("/")
def home():
    return render_template_string(
        HOME_TEMPLATE, 
        streams=STREAMS, 
        cookies_status="OK" if os.path.exists(COOKIES_FILE) else "MISSING"
    )

@app.route("/<stream_name>")
def stream(stream_name):
    if stream_name not in STREAMS:
        return "Stream not found", 404
    url = STREAMS[stream_name]
    log("SYSTEM", f"Incoming request: {stream_name}")
    return Response(generate_stream(url), mimetype="audio/mpeg")

# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    print("=" * 40)
    print("YOUTUBE AUDIO STREAM SERVER STARTING")
    print("=" * 40)
    app.run(host="0.0.0.0", port=8000, threaded=True)
