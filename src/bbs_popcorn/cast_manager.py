"""
Gestion du cast Chromecast pour BBS pOpcOrn.
Architecture daemon persistant : une connexion, plusieurs commandes.
"""
import subprocess
import threading
import json


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
        try:
            cast.media_controller.play_media(
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
    elif cmd == "PAUSE":
        try:
            cast.media_controller.pause()
        except Exception:
            pass
    elif cmd == "RESUME":
        try:
            cast.media_controller.play()
        except Exception:
            pass
    elif cmd == "VOL_UP":
        try:
            vol = min((cast.status.volume_level or 0.5) + 0.1, 1.0)
            cast.set_volume(vol)
        except Exception:
            pass
    elif cmd == "VOL_DOWN":
        try:
            vol = max((cast.status.volume_level or 0.5) - 0.1, 0.0)
            cast.set_volume(vol)
        except Exception:
            pass


pychromecast.discovery.stop_discovery(browser)
"""


class CastDaemon:
    """Daemon persistant pour un appareil Chromecast."""

    def __init__(self):
        self._proc = None
        self._write_lock = threading.Lock()  # protege les ecritures stdin
        self._read_lock = threading.Lock()   # protege les lectures stdout

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
                    with self._write_lock:
                        self._proc = proc
                    callback(True, None)
                else:
                    proc.terminate()
                    callback(False, line)
            except Exception as exc:
                callback(False, str(exc))
        threading.Thread(target=_run, daemon=True).start()

    def _write(self, cmd: str) -> bool:
        """Envoie une commande (lock ecriture seulement)."""
        with self._write_lock:
            if not self._proc or self._proc.poll() is not None:
                return False
            try:
                self._proc.stdin.write(cmd + "\n")
                self._proc.stdin.flush()
                return True
            except Exception:
                return False

    def _send(self, cmd: str) -> tuple:
        """Envoie commande et attend reponse."""
        with self._read_lock:
            if not self._write(cmd):
                return False, "daemon not running"
            try:
                response = self._proc.stdout.readline().strip()
                return response == "ok", response
            except Exception as exc:
                return False, str(exc)

    def cast_async(self, url: str, callback=None):
        def _run():
            ok, err = self._send("CAST " + url)
            if callback:
                callback(ok, err)
        threading.Thread(target=_run, daemon=True).start()

    def stop(self):
        """Envoie STOP sans attendre reponse (evite deadlock avec cast_async)."""
        self._write("STOP")

    def pause(self):
        self._write("PAUSE")

    def resume(self):
        self._write("RESUME")

    def vol_up(self):
        self._write("VOL_UP")

    def vol_down(self):
        self._write("VOL_DOWN")

    def quit(self):
        self._write("QUIT")
        with self._write_lock:
            if self._proc:
                try:
                    self._proc.terminate()
                except Exception:
                    pass
                self._proc = None

    def is_running(self) -> bool:
        with self._write_lock:
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
