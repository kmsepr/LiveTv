import os
import subprocess
import threading
import time
from flask import Flask, Response, render_template_string, request

app = Flask(__name__)

# =========================================================
# CONFIG
# =========================================================

STREAMS = {
    "media_one": "https://www.youtube.com/@mediaoneTVlive/live",
    # "asianet": "https://www.youtube.com/@asianetnews/live",
}

# =========================================================
# LOGGING
# =========================================================

def log(prefix, message):
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}][{prefix}] {message}", flush=True)

# =========================================================
# HTML TEMPLATE
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
        audio { width: 100%; margin-top: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔴 YouTube Audio Stream Server</h1>
        <p style="text-align:center; color:#9ca3af;">Client: TV | No Cookies Required</p>

        {% for name, url in streams.items() %}
        <div class="card">
            <div>{{ name.replace('_', ' ').title() }} <span class="badge">LIVE</span></div>
            <div class="url">Source: {{ url }}</div>
            <audio controls preload="none">
                <source src="/{{ name }}" type="audio/mpeg">
                Your browser does not support audio.
            </audio>
            <div style="margin-top:8px;">
                <b>Direct:</b> <a href="/{{ name }}">{{ request.host_url }}{{ name }}</a>
            </div>
        </div>
        {% endfor %}

        <div class="footer">
            Deploy: Koyeb | Check logs for "Downloading MPD manifest"
        </div>
    </div>
</body>
</html>
"""

# =========================================================
# STREAM FUNCTION
# =========================================================

def generate_stream(stream_name, url):
    session_id = f"{stream_name}-{int(time.time())}"
    log("SYSTEM", "=" * 60)
    log("SYSTEM", f"SESSION START [{session_id}]")
    log("SYSTEM", f"URL: {url}")

    # KEY: Use TV client. No cookies. Bypasses PO Token + Login required
    yt_cmd = [
        "yt-dlp",
        "-v",
        "-f", "bestaudio[abr<=96]/bestaudio/best",
        "-o", "-",
        "--no-warnings",
        "--live-from-start",
        "--retries", "10",
        "--fragment-retries", "10",
        "--extractor-args", "youtube:player_client=tv",
        "--user-agent", "Mozilla/5.0 (Chromium; CrOS x86_64 14541.0.0) AppleWebKit/537.36",
        "--no-check-certificates",
        "--force-ipv4", # helps with Koyeb IPv6 issues
        url
    ]

    ffmpeg_cmd = [
        "ffmpeg",
        "-loglevel", "error", # less spam. use 'info' or 'debug' if needed
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

    log("SYSTEM", f"YT-DLP CMD: {' '.join(yt_cmd)}")

    yt_process = subprocess.Popen(yt_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
    ffmpeg_process = subprocess.Popen(ffmpeg_cmd, stdin=yt_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)

    bytes_sent = 0

    def log_yt():
        for line in yt_process.stderr:
            log("YT-DLP", line.decode(errors="ignore").rstrip())

    def log_ffmpeg():
        for line in ffmpeg_process.stderr:
            log("FFMPEG", line.decode(errors="ignore").rstrip())

    threading.Thread(target=log_yt, daemon=True).start()
    threading.Thread(target=log_ffmpeg, daemon=True).start()

    try:
        while True:
            chunk = ffmpeg_process.stdout.read(4096)
            if not chunk:
                log("SYSTEM", f"NO DATA FROM FFMPEG. Bytes sent: {bytes_sent}")
                log("SYSTEM", f"yt-dlp exit code: {yt_process.poll()}")
                log("SYSTEM", f"ffmpeg exit code: {ffmpeg_process.poll()}")
                break
            bytes_sent += len(chunk)
            yield chunk

    except GeneratorExit:
        log("SYSTEM", "CLIENT DISCONNECTED")

    except Exception as e:
        log("SYSTEM", f"EXCEPTION: {e}")

    finally:
        log("SYSTEM", "CLEANING UP")
        for p, name in [(yt_process, "yt-dlp"), (ffmpeg_process, "ffmpeg")]:
            try:
                if p.poll() is None:
                    p.kill()
                    log("SYSTEM", f"{name} killed")
            except Exception as e:
                log("SYSTEM", f"Error killing {name}: {e}")
        log("SYSTEM", f"SESSION END [{session_id}] Total bytes: {bytes_sent}")
        log("SYSTEM", "=" * 60)

# =========================================================
# ROUTES
# =========================================================

@app.route("/")
def home():
    return render_template_string(HOME_TEMPLATE, streams=STREAMS)

@app.route("/<stream_name>")
def stream(stream_name):
    if stream_name not in STREAMS:
        log("ERROR", f"Stream not found: {stream_name}")
        return "Stream not found", 404

    url = STREAMS[stream_name]
    log("SYSTEM", f"INCOMING REQUEST: /{stream_name} from {request.remote_addr}")

    return Response(
        generate_stream(stream_name, url),
        mimetype="audio/mpeg",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    print("=" * 60)
    print("YOUTUBE AUDIO STREAM SERVER STARTING")
    print("Client: TV | No Cookies")
    print("=" * 60)
    app.run(host="0.0.0.0", port=8000, threaded=True)
