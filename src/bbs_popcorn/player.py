import re
import time
import threading
from gi.repository import GLib

from bbs_popcorn.cookies import CookieExporter
from bbs_popcorn.updater import Updater


class MpvPlayer:

    def __init__(self, cookie_db_path: str, cookie_export_path: str, win):
        self.cookie_db_path = cookie_db_path
        self.cookie_export_path = cookie_export_path
        self.win = win

        self.on_show_loading = None
        self.on_hide_loading = None

    # ─────────────────────────────
    # cookies (optional)
    # ─────────────────────────────

    def get_cookies(self):
        exporter = CookieExporter(self.cookie_db_path, self.cookie_export_path)
        if exporter.export():
            return self.cookie_export_path
        return None

    # ─────────────────────────────
    # url normalization
    # ─────────────────────────────

    def _prepare_url(self, url: str) -> str:
        match = re.search(r"[?&]list=([a-zA-Z0-9_-]+)", url)
        if match:
            return f"https://www.youtube.com/playlist?list={match.group(1)}"
        return url

    # ─────────────────────────────
    # public
    # ─────────────────────────────

    def play(self, url: str):
        threading.Thread(target=self._launch, args=(url,), daemon=True).start()

    # ─────────────────────────────
    # launch mpv
    # ─────────────────────────────

    def _launch(self, url: str):
        GLib.idle_add(self._show_loading)

        url = self._prepare_url(url)
        # Keep the loader visible briefly so users get immediate feedback.
        time.sleep(0.35)

        GLib.idle_add(self._hide_for_mpv)

        Updater.play(url)

        GLib.idle_add(self._show_after_mpv)

    # ─────────────────────────────
    # UI
    # ─────────────────────────────

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
