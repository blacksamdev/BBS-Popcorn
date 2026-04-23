import subprocess
import threading


class HostUpdater:

    def __init__(self, on_done=None):
        self.on_done = on_done

    def check_and_update(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run_cmd(self, cmd):
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    # ─────────────────────────────
    # yt-dlp CHECK ONLY
    # ─────────────────────────────

    def _check_ytdlp(self):
        try:
            r = self._run_cmd(["yt-dlp", "--version"])
            return f"yt-dlp: {r.stdout.strip()}"
        except Exception:
            return "yt-dlp: not available"

    # ─────────────────────────────
    # MPV CHECK ONLY
    # ─────────────────────────────

    def _check_mpv(self):
        try:
            r = self._run_cmd(["mpv", "--version"])
            first = r.stdout.splitlines()[0] if r.stdout else ""
            return f"mpv: {first}"
        except Exception:
            return "mpv: not available"

    # ─────────────────────────────
    # MAIN
    # ─────────────────────────────

    def _run(self):
        msg = "\n".join([
            self._check_ytdlp(),
            self._check_mpv()
        ])

        if self.on_done:
            from gi.repository import GLib
            GLib.idle_add(self.on_done, msg)
