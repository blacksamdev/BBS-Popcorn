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
        self.min_loader_seconds = 1.8
        self._play_lock = threading.Lock()
        self._is_playing = False

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
        with self._play_lock:
            if self._is_playing:
                print("[BBS Popcorn] MPV already running, ignoring click.")
                return
            self._is_playing = True
        threading.Thread(target=self._launch, args=(url,), daemon=True).start()

    # ─────────────────────────────
    # launch mpv
    # ─────────────────────────────

    def _launch(self, url: str):
        try:
            start_time = time.monotonic()
            GLib.idle_add(self._show_loading)

            url = self._prepare_url(url)
            cookies_path = self.get_cookies()
            if not cookies_path:
                print("[BBS Popcorn] Cookie export failed, aborting MPV launch.")
                GLib.idle_add(self._hide_loading_only)
                return

            process = Updater.start_play(url, cookies_path=cookies_path)
            elapsed = time.monotonic() - start_time
            remaining = self.min_loader_seconds - elapsed
            if remaining > 0:
                time.sleep(remaining)

            if process.poll() is not None:
                print(f"[BBS Popcorn] MPV exited early with code {process.returncode}.")
                GLib.idle_add(self._hide_loading_only)
                return

            GLib.idle_add(self._hide_for_mpv)
            return_code = process.wait()
            if return_code != 0:
                print(f"[BBS Popcorn] MPV exited with code {return_code}.")
            GLib.idle_add(self._show_after_mpv)
        except Exception as exc:
            print(f"[BBS Popcorn] MPV launch error: {exc}")
            GLib.idle_add(self._hide_loading_only)
        finally:
            with self._play_lock:
                self._is_playing = False

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

    def _hide_loading_only(self):
        if self.on_hide_loading:
            self.on_hide_loading()
        return False

    def _show_after_mpv(self):
        self.win.set_visible(True)
        self.win.present()
        return False
