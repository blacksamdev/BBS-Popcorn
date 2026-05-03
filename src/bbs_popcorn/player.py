import re
import time
import threading
import os
import json
import socket as _socket
from gi.repository import GLib

from bbs_popcorn.cookies import CookieExporter
from bbs_popcorn.logging_utils import log_event
from bbs_popcorn.resume_store import ResumeStore
from bbs_popcorn.updater import Updater

_MPV_IPC_SOCKET = "/tmp/bbs-popcorn-mpv.sock"


class MpvPlayer:

    def __init__(
        self,
        cookie_db_path: str,
        cookie_export_path: str,
        win,
        playback_profile: str = "gaming",
        sponsorblock_script_path: str = None,
    ):
        self.cookie_db_path = cookie_db_path
        self.cookie_export_path = cookie_export_path
        self.win = win
        self.playback_profile = playback_profile
        self.sponsorblock_script_path = sponsorblock_script_path
        self.quality_target = "1080"
        self.window_mode = "windowed"
        self.window_scale_percent = 80
        self.sponsorblock_enabled = False

        self.on_show_loading = None
        self.on_hide_loading = None
        self.on_show_notice = None
        self.on_status_change = None
        self._play_lock = threading.Lock()
        self._is_playing = False
        self._cookie_prefetch_thread = None
        self._mpv_idle_proc = None
        self._prewarm_thread = None
        self._resume = ResumeStore()
        self._tracked_pos: float = 0.0
        self._tracked_duration: float | None = None
        self._tracking = False

    # ─────────────────────────────
    # cookies (optional)
    # ─────────────────────────────

    def get_cookies(self):
        exporter = CookieExporter(self.cookie_db_path, self.cookie_export_path)
        if exporter.export():
            return self.cookie_export_path
        return None

    def cleanup(self):
        """Appelé à la fermeture de l'app : termine le process idle et supprime le socket."""
        if self._mpv_idle_proc and self._mpv_idle_proc.poll() is None:
            try:
                self._mpv_idle_proc.terminate()
            except Exception:
                pass
        try:
            os.remove(_MPV_IPC_SOCKET)
        except OSError:
            pass
        log_event("Player cleanup effectue.")

    def prefetch_cookies(self):
        """Export cookies in background so they are ready on next play."""
        if self._cookie_prefetch_thread and self._cookie_prefetch_thread.is_alive():
            return
        self._cookie_prefetch_thread = threading.Thread(
            target=self.get_cookies, daemon=True
        )
        self._cookie_prefetch_thread.start()

    def prewarm_mpv(self):
        """Launch MPV in idle mode so the Flatpak runtime is loaded and ready."""
        if self._prewarm_thread and self._prewarm_thread.is_alive():
            return
        self._prewarm_thread = threading.Thread(target=self._do_prewarm, daemon=True)
        self._prewarm_thread.start()

    def _do_prewarm(self):
        # Terminate any lingering idle process and remove stale socket.
        if self._mpv_idle_proc and self._mpv_idle_proc.poll() is None:
            try:
                self._mpv_idle_proc.terminate()
            except Exception:
                pass
        try:
            os.remove(_MPV_IPC_SOCKET)
        except OSError:
            pass

        self._mpv_idle_proc = Updater.start_idle(
            _MPV_IPC_SOCKET,
            cookies_path=self.cookie_export_path,
            quality_target=self.quality_target,
            window_mode=self.window_mode,
            window_scale_percent=self.window_scale_percent,
            sponsorblock_enabled=self.sponsorblock_enabled,
            sponsorblock_script_path=self.sponsorblock_script_path,
        )
        # Wait for MPV to create the IPC socket (typically < 1 s).
        deadline = time.monotonic() + 4.0
        while time.monotonic() < deadline:
            if os.path.exists(_MPV_IPC_SOCKET):
                log_event("MPV pre-warms: IPC socket pret.", level="debug")
                return
            time.sleep(0.05)
        log_event("MPV pre-warm: socket absent apres delai.", level="debug")

    def _ipc_loadfile(self, url: str, start_pos: float = None) -> bool:
        """Send a loadfile command to the pre-warmed MPV via IPC socket."""
        try:
            sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect(_MPV_IPC_SOCKET)
            options = {}
            if start_pos and start_pos > 0:
                options["start"] = f"{start_pos:.1f}"
            cmd = ["loadfile", url, "replace"]
            if options:
                cmd.append(options)
            msg = json.dumps({"command": cmd}).encode() + b"\n"
            sock.sendall(msg)
            sock.close()
            return True
        except Exception as exc:
            log_event(f"IPC loadfile echec: {exc}", level="debug")
            return False

    def _ipc_get_property(self, prop: str):
        """Query a single MPV property via IPC. Returns parsed value or None."""
        try:
            sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect(_MPV_IPC_SOCKET)
            msg = json.dumps({"command": ["get_property", prop]}).encode() + b"\n"
            sock.sendall(msg)
            buf = b""
            while b"\n" not in buf:
                chunk = sock.recv(1024)
                if not chunk:
                    break
                buf += chunk
            sock.close()
            resp = json.loads(buf.split(b"\n")[0])
            if resp.get("error") == "success":
                return resp.get("data")
        except Exception:
            pass
        return None

    def _track_position(self, url: str):
        """Poll time-pos and duration every 5 s while MPV is playing."""
        self._tracking = True
        self._tracked_pos = 0.0
        self._tracked_duration = None
        while self._tracking and self._is_playing:
            pos = self._ipc_get_property("time-pos")
            dur = self._ipc_get_property("duration")
            if isinstance(pos, (int, float)):
                self._tracked_pos = float(pos)
            if isinstance(dur, (int, float)) and dur > 0:
                self._tracked_duration = float(dur)
            time.sleep(5.0)
        self._tracking = False

    def _wait_with_timeout(self, process, timeout: int = 120) -> int:
        """Attend la fin du process avec un timeout en secondes. Retourne le code de retour."""
        result = [None]

        def _waiter():
            result[0] = process.wait()

        t = threading.Thread(target=_waiter, daemon=True)
        t.start()
        t.join(timeout=timeout)
        if t.is_alive():
            log_event(f"MPV timeout apres {timeout}s, terminaison forcee.", level="debug")
            try:
                process.terminate()
            except Exception:
                pass
            t.join(timeout=5)
            return process.returncode if process.returncode is not None else -1
        return result[0]

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
                self._status("Lecture deja en cours.")
                return
            self._is_playing = True
        self._status("Preparation de la lecture...")
        threading.Thread(target=self._launch, args=(url,), daemon=True).start()

    def update_playback_settings(
        self,
        quality_target: str,
        window_mode: str,
        window_scale_percent: int,
        sponsorblock_enabled: bool = False,
    ):
        self.quality_target = quality_target
        self.window_mode = window_mode
        self.window_scale_percent = window_scale_percent
        self.sponsorblock_enabled = sponsorblock_enabled
        if not self._is_playing:
            self.prewarm_mpv()

    # ─────────────────────────────
    # launch mpv
    # ─────────────────────────────

    def _launch(self, url: str):
        cookies_path = None
        try:
            GLib.idle_add(self._show_loading)

            url = self._prepare_url(url)
            # Use pre-exported cookies if ready, otherwise export now
            if self._cookie_prefetch_thread and self._cookie_prefetch_thread.is_alive():
                self._cookie_prefetch_thread.join()
            cookies_path = self.get_cookies() if not os.path.exists(self.cookie_export_path) else self.cookie_export_path
            if not cookies_path:
                print("[BBS Popcorn] Cookie export failed, aborting MPV launch.")
                GLib.idle_add(self._hide_loading_only)
                return

            # Use pre-warmed MPV via IPC if available, otherwise spawn fresh.
            start_pos = self._resume.get(url)
            with self._play_lock:
                ipc_ready = (
                    os.path.exists(_MPV_IPC_SOCKET)
                    and self._mpv_idle_proc is not None
                    and self._mpv_idle_proc.poll() is None
                )
                idle_proc = self._mpv_idle_proc if ipc_ready else None
                if ipc_ready:
                    self._mpv_idle_proc = None

            if idle_proc and self._ipc_loadfile(url, start_pos=start_pos):
                process = idle_proc
                time.sleep(0.3)
            else:
                process = self._start_process(
                    url, cookies_path,
                    use_fallback_format=False,
                    start_pos=start_pos,
                    ipc_socket_path=_MPV_IPC_SOCKET,
                )

            if process.poll() is not None:
                if self._retry_with_fallback(url, cookies_path):
                    return
                print(f"[BBS Popcorn] MPV exited early with code {process.returncode}.")
                log_event(f"mpv exited early code={process.returncode} url={url}")
                self._status("Impossible de lancer la lecture.")
                notice = Updater.get_upcoming_live_message(url)
                if notice and self.on_show_notice:
                    GLib.idle_add(self.on_show_notice, notice)
                else:
                    GLib.idle_add(self._hide_loading_only)
                return

            self._status("Lecture en cours.")
            GLib.idle_add(self._hide_for_mpv)
            threading.Thread(
                target=self._track_position, args=(url,), daemon=True
            ).start()
            return_code = self._wait_with_timeout(process)
            self._tracking = False
            self._resume.set(url, self._tracked_pos, self._tracked_duration)
            if return_code != 0:
                print(f"[BBS Popcorn] MPV exited with code {return_code}.")
                log_event(f"mpv exited code={return_code} url={url}")
                self._status("Lecture terminee avec avertissement.")
                notice = Updater.get_upcoming_live_message(url)
                if notice and self.on_show_notice:
                    GLib.idle_add(self.on_show_notice, notice)
            else:
                self._status("Lecture terminee.")
            GLib.idle_add(self._show_after_mpv)
        except Exception as exc:
            print(f"[BBS Popcorn] MPV launch error: {exc}")
            log_event(f"mpv launch error: {exc}")
            self._status("Erreur de lancement video.")
            GLib.idle_add(self._hide_loading_only)
        finally:
            self._cleanup_exported_cookies(cookies_path)
            with self._play_lock:
                self._is_playing = False
            self.prefetch_cookies()
            self.prewarm_mpv()

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

    def _status(self, text: str):
        if self.on_status_change:
            GLib.idle_add(self.on_status_change, text)
        log_event(text)

    def _start_process(
        self,
        url: str,
        cookies_path: str,
        use_fallback_format: bool,
        start_pos: float = None,
        ipc_socket_path: str = None,
    ):
        return Updater.start_play(
            url,
            cookies_path=cookies_path,
            playback_profile=self.playback_profile,
            use_fallback_format=use_fallback_format,
            quality_target=self.quality_target,
            window_mode=self.window_mode,
            window_scale_percent=self.window_scale_percent,
            start_pos=start_pos,
            ipc_socket_path=ipc_socket_path,
            sponsorblock_enabled=self.sponsorblock_enabled,
            sponsorblock_script_path=self.sponsorblock_script_path,
        )

    def _retry_with_fallback(self, url: str, cookies_path: str) -> bool:
        self._status("Format compatible: nouvelle tentative...")
        process = self._start_process(
            url, cookies_path,
            use_fallback_format=True,
            ipc_socket_path=_MPV_IPC_SOCKET,
        )
        time.sleep(0.5)
        if process.poll() is not None:
            return False
        self._status("Lecture en cours (mode compatible).")
        GLib.idle_add(self._hide_for_mpv)
        threading.Thread(
            target=self._track_position, args=(url,), daemon=True
        ).start()
        return_code = self._wait_with_timeout(process)
        self._tracking = False
        self._resume.set(url, self._tracked_pos, self._tracked_duration)
        if return_code != 0:
            log_event(f"mpv fallback exited code={return_code} url={url}")
            self._status("Lecture terminee avec avertissement.")
        else:
            self._status("Lecture terminee.")
        GLib.idle_add(self._show_after_mpv)
        return True

    def _cleanup_exported_cookies(self, cookies_path: str):
        if not cookies_path:
            return
        if cookies_path != self.cookie_export_path:
            return
        if not os.path.exists(cookies_path):
            return
        try:
            os.remove(cookies_path)
            log_event("cookies.txt supprime apres lecture MPV.")
        except OSError as exc:
            log_event(f"echec suppression cookies.txt: {exc}")
