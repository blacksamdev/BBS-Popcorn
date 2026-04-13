import os
import time
import tempfile
import subprocess
import threading
import socket
import json
from gi.repository import GLib

from cookies import CookieExporter


class MpvPlayer:
    def __init__(self, cookie_db_path: str, cookie_export_path: str, win):
        self.cookie_db_path     = cookie_db_path
        self.cookie_export_path = cookie_export_path
        self.win                = win

        self.on_show_loading = None
        self.on_hide_loading = None

    # ── Cookies ──────────────────────────────────

    def get_fresh_cookies(self) -> str | None:
        exporter = CookieExporter(self.cookie_db_path, self.cookie_export_path)
        if exporter.export():
            return self.cookie_export_path
        return None

    # ── Lancement ────────────────────────────────

    def play(self, url: str):
        threading.Thread(
            target=self._launch,
            args=(url,),
            daemon=True
        ).start()

    def _launch(self, url: str):
        GLib.idle_add(self._show_loading)

        ipc_socket = tempfile.mktemp(prefix="bbspopcorn_")

        # MPV Flatpak
        if os.path.exists("/.flatpak-info"):
            mpv_cmd = ["flatpak-spawn", "--host", "flatpak", "run", "io.mpv.Mpv"]
        else:
            mpv_cmd = ["flatpak", "run", "io.mpv.Mpv"]

        cmd = mpv_cmd + [
            "--ytdl-format=bestvideo+bestaudio/best",
            "--demuxer-max-bytes=500MiB",
            "--demuxer-max-back-bytes=100MiB",
            "--hwdec=auto-safe",
            "--vo=gpu",
            "--gpu-api=opengl",
            "--force-window=yes",
            "--window-maximized=yes",
            "--ontop=yes",
            "--mute=no",
            "--volume=100",
            f"--input-ipc-server={ipc_socket}",
        ]

        # Cookies désactivés temporairement (format WebKit incompatible yt-dlp)
        # cookie_file = self.get_fresh_cookies()
        # if cookie_file:
        #     cmd += ["--ytdl-raw-options=cookies=" + cookie_file]

        cmd.append(url)
        print(f"[popcorn] Commande : {' '.join(cmd)}")

        proc = subprocess.Popen(cmd)

        # Attend que le socket IPC apparaisse = MPV prêt
        waited = 0
        while not os.path.exists(ipc_socket) and waited < 15:
            time.sleep(0.2)
            waited += 0.2

        GLib.idle_add(self._hide_for_mpv)

        proc.wait()

        if os.path.exists(ipc_socket):
            os.remove(ipc_socket)

        GLib.idle_add(self._show_after_mpv)

    # ── Callbacks UI ─────────────────────────────

    def _show_loading(self):
        if self.on_show_loading:
            self.on_show_loading()
        return False

    def _hide_for_mpv(self):
        if self.on_hide_loading:
            self.on_hide_loading()
        self.win.set_visible(False)
        return False

    def _show_after_mpv(self):
        self.win.set_visible(True)
        self.win.present()
        return False
