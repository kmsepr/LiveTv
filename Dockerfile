from flask import Flask, Response
import subprocess
import threading
import os

app = Flask(__name__)

# ==========================================
# CHANNELS
# ==========================================

YOUTUBE_STREAMS = {
    "media_one": "https://www.youtube.com/watch?v=-8d8-c0yvyU",

    # Test stream
    "lofi": "https://www.youtube.com/watch?v=jfKfPfyJRdk"
}

# ==========================================
# ENVIRONMENT VARIABLES
# ==========================================

# Set in Koyeb Secrets:
# PROXY_URL=http://username:password@host:port

PROXY = os.getenv("PROXY_URL", "")

# Optional custom cookies path
COOKIES_FILE = os.getenv(
    "COOKIES_FILE",
    "/mnt/data/cookies.txt"
)

# ==========================================
# FFMPEG SETTINGS
# ==========================================

FFMPEG_CMD = [
    "ffmpeg",

    "-loglevel", "info",

    "-i", "pipe:0",

    "-vn",

    # low bandwidth
    "-ac", "1",
    "-ar", "22050",
    "-b:a", "40k",

    "-f", "mp3",
    "-"
]


# ==========================================
# REALTIME LOGGING
# ==========================================

def log_output(pipe, prefix):

    for line in iter(pipe.readline, b''):

        try:
            print(f"[{prefix}] {line.decode(errors='ignore').rstrip()}")

        except Exception as e:
            print(f"[LOG ERROR] {e}")


# ==========================================
# STREAM GENERATOR
# ==========================================

def generate_stream(url):

    ytdlp_cmd = [

        "yt-dlp",

        # verbose logs
        "-v",

        # best audio
        "-f", "251/bestaudio/best",

        # stdout output
        "-o", "-",

        "--no-warnings",

        # better YouTube compatibility
        "--extractor-args",
        "youtube:player_client=tv_embedded,web"
    ]

    # ==========================================
    # COOKIES
    # ==========================================

    if os.path.exists(COOKIES_FILE):

        print(f"[SYSTEM] Using cookies: {COOKIES_FILE}")

        ytdlp_cmd += [
            "--cookies",
            COOKIES_FILE
        ]

    else:

        print("[SYSTEM] cookies.txt NOT FOUND")

    # ==========================================
    # PROXY
    # ==========================================

    if PROXY.strip():

        print("[SYSTEM] Proxy ENABLED")

        ytdlp_cmd += [
            "--proxy",
            PROXY
        ]

    else:

        print("[SYSTEM] Proxy DISABLED")

    # ==========================================
    # URL
    # ==========================================

    ytdlp_cmd.append(url)

    # ==========================================
    # START YT-DLP
    # ==========================================

    print("[SYSTEM] Starting yt-dlp...")
    print(" ".join(ytdlp_cmd))

    ytdlp = subprocess.Popen(
        ytdlp_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )

    threading.Thread(
        target=log_output,
        args=(ytdlp.stderr, "YT-DLP"),
        daemon=True
    ).start()

    # ==========================================
    # START FFMPEG
    # ==========================================

    print("[SYSTEM] Starting ffmpeg...")
    print(" ".join(FFMPEG_CMD))

    ffmpeg = subprocess.Popen(
        FFMPEG_CMD,
        stdin=ytdlp.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )

    threading.Thread(
        target=log_output,
        args=(ffmpeg.stderr, "FFMPEG"),
        daemon=True
    ).start()

    # ==========================================
    # STREAM LOOP
    # ==========================================

    while True:

        try:

            data = ffmpeg.stdout.read(1024)

            if not data:
                print("[SYSTEM] Stream ended")
                break

            yield data

        except Exception as e:

            print(f"[ERROR] {e}")
            break

    # ==========================================
    # CLEANUP
    # ==========================================

    print("[SYSTEM] Cleaning up processes")

    try:
        ytdlp.kill()
    except:
        pass

    try:
        ffmpeg.kill()
    except:
        pass


# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def home():

    html = """
    <html>

    <head>

        <title>YouTube Audio Streams</title>

        <style>

            body {
                background: #111;
                color: white;
                font-family: Arial;
                padding: 20px;
            }

            h1 {
                color: #00ff99;
            }

            a {
                color: #00ccff;
                text-decoration: none;
                font-size: 20px;
            }

            li {
                margin: 14px 0;
            }

        </style>

    </head>

    <body>

        <h1>Available Channels</h1>

        <ul>
    """

    for name in YOUTUBE_STREAMS:

        html += f'<li>🎧 <a href="/{name}">{name}</a></li>'

    html += """
        </ul>

    </body>
    </html>
    """

    return html


# ==========================================
# COOKIES DEBUG
# ==========================================

@app.route("/cookies")
def cookies_check():

    if not os.path.exists(COOKIES_FILE):
        return "cookies.txt NOT FOUND"

    try:

        with open(
            COOKIES_FILE,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as f:

            first_lines = "".join(f.readlines()[:20])

        return f"<pre>{first_lines}</pre>"

    except Exception as e:
        return str(e)


# ==========================================
# HEALTH CHECK
# ==========================================

@app.route("/health")
def health():

    return {
        "status": "running",
        "proxy_enabled": bool(PROXY.strip()),
        "cookies_exists": os.path.exists(COOKIES_FILE),
        "channels": list(YOUTUBE_STREAMS.keys())
    }


# ==========================================
# STREAM ENDPOINT
# ==========================================

@app.route("/<channel>")
def stream(channel):

    print(f"[SYSTEM] Incoming request: {channel}")

    url = YOUTUBE_STREAMS.get(channel)

    if not url:

        print("[ERROR] Channel not found")
        return "Channel not found", 404

    print(f"[SYSTEM] Streaming URL: {url}")

    return Response(
        generate_stream(url),
        mimetype="audio/mpeg"
    )


# ==========================================
# SERVER START
# ==========================================

if __name__ == "__main__":

    print("[SYSTEM] Server starting on port 8000")

    app.run(
        host="0.0.0.0",
        port=8000,
        threaded=True
    )
