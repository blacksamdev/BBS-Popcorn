"""
Gestion du cast Chromecast pour BBS pOpcOrn.
Utilise pychromecast via flatpak-spawn --host (installé sur le host).
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

_CAST_SCRIPT = """
import pychromecast, sys
host = sys.argv[1]
port = int(sys.argv[2])
url  = sys.argv[3]
chromecasts, browser = pychromecast.get_chromecasts()
if not chromecasts:
    sys.exit(1)
cast = next((c for c in chromecasts if c.cast_info.host == host), None)
if not cast:
    pychromecast.discovery.stop_discovery(browser)
    sys.exit(1)
cast.wait()
cast.media_controller.play_media(url, "video/mp4")
cast.media_controller.block_until_active()
pychromecast.discovery.stop_discovery(browser)
sys.stdout.write("ok")
"""


def discover_async(callback):
    """Découvre les Chromecasts en arrière-plan.
    callback(devices, error) — devices = liste de dicts {name, host, port, model}
    """
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


_STOP_SCRIPT = """
import pychromecast, sys
host = sys.argv[1]
port = int(sys.argv[2])
chromecasts, browser = pychromecast.get_chromecasts()
if not chromecasts:
    sys.exit(1)
cast = next((c for c in chromecasts if c.cast_info.host == host), None)
if not cast:
    pychromecast.discovery.stop_discovery(browser)
    sys.exit(1)
cast.wait()
cast.media_controller.stop()
pychromecast.discovery.stop_discovery(browser)
sys.stdout.write("ok")
"""

def stop_async(host: str, port: int = 8009, callback=None):
    """Stoppe le cast sur l'appareil host."""
    def _run():
        try:
            result = subprocess.run(
                ["flatpak-spawn", "--host", "python3", "-c",
                 _STOP_SCRIPT, host, str(port)],
                capture_output=True, text=True, timeout=15
            )
            if callback:
                callback(result.returncode == 0, result.stderr.strip())
        except Exception as exc:
            if callback:
                callback(False, str(exc))
    threading.Thread(target=_run, daemon=True).start()

def cast_async(host: str, stream_url: str, port: int = 8009, callback=None):
    """Envoie le flux au Chromecast. callback(ok: bool, error: str)"""
    def _run():
        try:
            result = subprocess.run(
                ["flatpak-spawn", "--host", "python3", "-c",
                 _CAST_SCRIPT, host, str(port), stream_url],
                capture_output=True, text=True, timeout=30
            )
            if callback:
                callback(result.returncode == 0, result.stderr.strip())
        except Exception as exc:
            if callback:
                callback(False, str(exc))
    threading.Thread(target=_run, daemon=True).start()


def resolve_stream_url(video_url: str) -> str | None:
    """Résout l'URL YouTube en flux h264 direct via yt-dlp (sandbox)."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--no-playlist", "--dump-single-json", video_url],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return None
        info = json.loads(result.stdout)
        # Préférer h264 avec audio
        url = next(
            (f["url"] for f in info.get("formats", [])
             if f.get("vcodec", "").startswith("avc1")
             and f.get("acodec") not in (None, "none")),
            info.get("url")
        )
        return url
    except Exception:
        return None
