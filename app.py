import subprocess
import requests
from flask import Flask, Response, render_template_string, abort

app = Flask(__name__)

# -----------------------
# TV Streams
# -----------------------
TV_STREAMS = {
    "safari_tv": "https://j78dp346yq5r-hls-live.5centscdn.com/safari/live.stream/chunks.m3u8",
    "dd_sports": "https://cdn-6.pishow.tv/live/13/master.m3u8",
    "dd_malayalam": "https://d3eyhgoylams0m.cloudfront.net/v1/manifest/93ce20f0f52760bf38be911ff4c91ed02aa2fd92/ed7bd2c7-8d10-4051-b397-2f6b90f99acb/562ee8f9-9950-48a0-ba1d-effa00cf0478/2.m3u8",
    "mazhavil_manorama": "https://yuppmedtaorire.akamaized.net/v1/master/a0d007312bfd99c47f76b77ae26b1ccdaae76cb1/mazhavilmanorama_nim_https/050522/mazhavilmanorama/playlist.m3u8",
    "victers_tv": "https://932y4x26ljv8-hls-live.5centscdn.com/victers/tv.stream/chunks.m3u8",
    "france_24": "https://live.france24.com/hls/live/2037218/F24_EN_HI_HLS/master_500.m3u8",
}

# -----------------------
# Logos
# -----------------------
CHANNEL_LOGOS = {
    "safari_tv": "https://i.imgur.com/dSOfYyh.png",
    "victers_tv": "https://i.imgur.com/kj4OEsb.png",
    "france_24": "https://upload.wikimedia.org/wikipedia/commons/c/c1/France_24_logo_%282013%29.svg",
    "mazhavil_manorama": "https://i.imgur.com/fjgzW20.png",
    "dd_malayalam": "https://i.imgur.com/ywm2dTl.png",
    "dd_sports": "https://i.imgur.com/J2Ky5OO.png",
}

# -----------------------
# HOME (SPB STYLE UI)
# -----------------------
@app.route("/")
def home():
    channels = list(TV_STREAMS.keys())

    html = """
<html>
<head>
<title>KM TV</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
body {
    margin:0;
    font-family:sans-serif;
    background: linear-gradient(#0a6d6d, #0b2f2f);
    color:#fff;
}

/* Top bar */
.topbar {
    padding:10px;
    background:#0b5c5c;
    font-size:18px;
}

/* Preview */
.preview {
    text-align:center;
    padding:10px;
}

.preview video {
    width:95%;
    max-width:320px;
    background:#000;
}

/* Schedule */
.schedule {
    padding:10px;
    font-size:15px;
}

/* Channel strip */
.strip {
    display:flex;
    overflow-x:auto;
    gap:10px;
    padding:10px;
    background:#0b5c5c;
}

.channel {
    min-width:90px;
    background:#fff;
    border-radius:10px;
    padding:5px;
    text-align:center;
}

.channel img {
    width:60px;
    height:40px;
    object-fit:contain;
}

.channel a {
    display:block;
    font-size:12px;
    color:#000;
    text-decoration:none;
}

/* Footer */
.footer {
    display:flex;
    justify-content:space-between;
    padding:10px;
    background:#083c3c;
}
</style>

</head>

<body>

<div class="topbar">KM TV</div>

<div class="preview">
    <video controls autoplay>
        <source src="{{ first }}">
    </video>
</div>

<div class="schedule">
<b>12:00</b> News<br>
<b>12:30</b> In Focus<br>
<b>13:00</b> News<br>
<b>13:30</b> Program<br>
</div>

<div class="strip">
{% for key in channels %}
<div class="channel">
    <a href="/watch/{{ key }}">
        <img src="{{ logos.get(key) }}">
        {{ key.replace('_',' ').title() }}
    </a>
</div>
{% endfor %}
</div>

<div class="footer">
<span>Exit</span>
<span>Menu</span>
</div>

</body>
</html>
"""
    return render_template_string(
        html,
        channels=channels,
        logos=CHANNEL_LOGOS,
        first=TV_STREAMS[channels[0]]
    )

# -----------------------
# WATCH PLAYER
# -----------------------
@app.route("/watch/<channel>")
def watch(channel):
    if channel not in TV_STREAMS:
        abort(404)

    channels = list(TV_STREAMS.keys())
    i = channels.index(channel)

    prev_ch = channels[(i - 1) % len(channels)]
    next_ch = channels[(i + 1) % len(channels)]

    url = TV_STREAMS[channel]

    html = f"""
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{channel}</title>

<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>

<style>
body {{ background:#000; color:#fff; text-align:center; margin:0; padding:10px; }}
video {{ width:95%; max-width:720px; background:#000; }}
a {{ color:#0f0; display:inline-block; margin:10px; font-size:18px; }}
</style>

<script>
document.addEventListener("DOMContentLoaded", function() {{
  var video = document.getElementById("player");
  var src = "{url}";

  if (video.canPlayType("application/vnd.apple.mpegurl")) {{
    video.src = src;
  }} else if (Hls.isSupported()) {{
    var hls = new Hls();
    hls.loadSource(src);
    hls.attachMedia(video);
  }}
}});

document.addEventListener("keydown", function(e) {{
  if(e.key==="4") window.location="/watch/{prev_ch}";
  if(e.key==="6") window.location="/watch/{next_ch}";
  if(e.key==="0") window.location="/";
}});
</script>

</head>
<body>

<h3>{channel.replace('_',' ').title()}</h3>

<video id="player" controls autoplay></video>

<br>
<a href="/">⬅ Home</a>
<a href="/watch/{prev_ch}">⏮ Prev</a>
<a href="/watch/{next_ch}">⏭ Next</a>
<a href="/audio/{channel}">🎵 Audio</a>

</body>
</html>
"""
    return html

# -----------------------
# AUDIO STREAM
# -----------------------
@app.route("/audio/<channel>")
def audio(channel):
    if channel not in TV_STREAMS:
        return "Invalid channel"

    url = TV_STREAMS[channel]

    def generate():
        cmd = [
            "ffmpeg", "-i", url,
            "-vn",
            "-ac", "1",
            "-b:a", "40k",
            "-f", "mp3",
            "pipe:1"
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            while True:
                data = proc.stdout.read(1024)
                if not data:
                    break
                yield data
        finally:
            proc.terminate()

    return Response(generate(), mimetype="audio/mpeg")

# -----------------------
# RUN
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)