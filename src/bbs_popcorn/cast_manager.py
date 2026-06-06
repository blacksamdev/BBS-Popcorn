"""
Gestion du cast Chromecast pour BBS pOpcOrn.
Architecture daemon persistant : une connexion, plusieurs commandes.
"""
import subprocess
import threading
import json

SPLASH_URL = "https://blacksamdev.github.io/BBS-Popcorn/splash.png"

_DISCOVER_SCRIPT = """
import pychromecast, json, sys
chromecasts, browser = pychromecast.get_chromecasts()
result = [{"name": c.name, "host": c.cast_info.host,
           "port": c.cast_info.port, "model": c.model_name}
          for c in chromecasts]
sys.stdout.write(json.dumps(result))
sys.stdout.flush()
pychromecast.discovery.stop_discovery(browser)
"""

_DAEMON_SCRIPT = """
import pychromecast, sys

host = sys.argv[1]

# Decouverte unique
chromecasts, browser = pychromecast.get_chromecasts(timeout=5)
cast = next((c for c in chromecasts if c.cast_info.host == host), None)
if not cast:
    sys.stdout.write("error: not found\\n")
    sys.stdout.flush()
    pychromecast.discovery.stop_discovery(browser)
    sys.exit(1)

cast.wait()
sys.stdout.write("ready\\n")
sys.stdout.flush()

# Boucle de commandes
for line in sys.stdin:
    cmd = line.strip()
    if not cmd:
        continue
    if cmd == "QUIT":
        break
    elif cmd == "SPLASH":
        try:
            cast.media_controller.play_media(
                "https://blacksamdev.github.io/BBS-Popcorn/splash.png",
                "image/png"
            )
            sys.stdout.write("ok\\n")
        except Exception as e:
            sys.stdout.write("error: " + str(e) + "\\n")
        sys.stdout.flush()
    elif cmd.startswith("CAST "):
        url = cmd[5:]
        try:
            cast.media_controller.play_media(url, "video/mp4")
            cast.media_controller.block_until_active()
            sys.stdout.write("ok\\n")
        except Exception as e:
            sys.stdout.write("error: " + str(e) + "\\n")
        sys.stdout.flush()
    elif cmd == "STOP":
        try:
            cast.quit_app()
            sys.stdout.write("ok\\n")
        except Exception:
            sys.stdout.write("ok\\n")
        sys.stdout.flush()

pychromecast.discovery.stop_discovery(browser)
"""


class CastDaemon:
    """Daemon persistant pour un appareil Chromecast."""

    def __init__(self):
        self._proc = None
        self._lock = threading.Lock()

    def start_async(self, host: str, callback):
        """Lance le daemon. callback(ok: bool, error: str)"""
        def _run():
            try:
                proc = subprocess.Popen(
                    ["flatpak-spawn", "--host", "python3", "-c",
                     _DAEMON_SCRIPT, host],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                line = proc.stdout.readline().strip()
                if line == "ready":
                    with self._lock:
                        self._proc = proc
                    callback(True, None)
                else:
                    proc.terminate()
                    callback(False, line)
            except Exception as exc:
                callback(False, str(exc))
        threading.Thread(target=_run, daemon=True).start()

    def _send(self, cmd: str) -> tuple:
        with self._lock:
            if not self._proc or self._proc.poll() is not None:
                return False, "daemon not running"
            try:
                self._proc.stdin.write(cmd + "\n")
                self._proc.stdin.flush()
                response = self._proc.stdout.readline().strip()
                return response == "ok", response
            except Exception as exc:
                return False, str(exc)

    def splash(self):
        return self._send("SPLASH")

    def cast_async(self, url: str, callback=None):
        def _run():
            ok, err = self._send("CAST " + url)
            if callback:
                callback(ok, err)
        threading.Thread(target=_run, daemon=True).start()

    def stop(self):
        return self._send("STOP")

    def quit(self):
        with self._lock:
            if self._proc:
                try:
                    self._proc.stdin.write("QUIT\n")
                    self._proc.stdin.flush()
                    self._proc.terminate()
                except Exception:
                    pass
                self._proc = None

    def is_running(self) -> bool:
        with self._lock:
            return self._proc is not None and self._proc.poll() is None


def discover_async(callback):
    """Decouvre les Chromecasts. callback(devices, error)"""
    def _run():
        try:
            result = subprocess.run(
                ["flatpak-spawn", "--host", "python3", "-c", _DISCOVER_SCRIPT],
                capture_output=True, text=True, timeout=12
            )
            if result.returncode == 0 and result.stdout.strip():
                callback(json.loads(result.stdout), None)
            elif "pychromecast" in result.stderr:
                callback(None, "missing")
            else:
                callback([], None)
        except Exception as exc:
            callback(None, str(exc))
    threading.Thread(target=_run, daemon=True).start()


def resolve_stream_url(video_url: str) -> str | None:
    """Resout l'URL YouTube en flux h264 direct via yt-dlp."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--no-playlist", "--dump-single-json", video_url],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return None
        info = json.loads(result.stdout)
        url = next(
            (f["url"] for f in info.get("formats", [])
             if f.get("vcodec", "").startswith("avc1")
             and f.get("acodec") not in (None, "none")),
            info.get("url")
        )
        return url
    except Exception:
        return None
