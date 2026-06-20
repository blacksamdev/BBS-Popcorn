import re
import shutil
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

# Socket IPC : chemin différent selon Flatpak ou natif
# - Flatpak : ~/.var/app/io.mpv.Mpv/ accessible par les deux sandboxes
# - Natif   : XDG_RUNTIME_DIR partagé entre le process et MPV système
_IS_FLATPAK = os.path.exists("/app")
if _IS_FLATPAK:
    _MPV_IPC_SOCKET = os.path.expanduser(
        "~/.var/app/io.mpv.Mpv/bbs-popcorn-mpv.sock"
    )
else:
    _MPV_IPC_SOCKET = os.path.join(
        GLib.get_user_runtime_dir(), "bbs-popcorn-mpv.sock"
    )
_MPV_SCRIPTS_DIR = os.path.expanduser("~/.var/app/io.mpv.Mpv/config/mpv/scripts")


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
        self.audio_lang = "auto"
        self.subtitle_lang = "none"
        self.subtitle_fallback = False

        self.on_show_loading = None
        self.on_hide_loading = None
        self.on_show_notice = None
        self.on_status_change = None
        self._play_lock = threading.Lock()
        self._is_playing = False
        self._cookie_prefetch_thread = None
        self._mpv_idle_proc = None
        self._prewarm_thread = None
        self._ytdlp_proc = None
        self._playback_ended = threading.Event()
        self._stream_started = False
        self._resume = ResumeStore()
        self._tracked_pos: float = 0.0
        self._tracked_duration: float | None = None
        self._tracking = False

    # ─────────────────────────────
    # cookies
    # ─────────────────────────────

    def get_cookies(self):
        exporter = CookieExporter(self.cookie_db_path, self.cookie_export_path)
        if exporter.export():
            return self.cookie_export_path
        return None

    def cleanup(self):
        """Fermeture propre : IPC quit → terminate wrapper → pkill fallback."""
        # 1. Demander à MPV idle de quitter via IPC
        self._ipc_command("quit")
        time.sleep(0.3)
        # 2. Terminer le wrapper flatpak-spawn
        with self._play_lock:
            proc = self._mpv_idle_proc
            self._mpv_idle_proc = None
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                pass
            # Fallback SIGKILL si terminate insuffisant
            if proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass
        # 3. Tuer le subprocess yt-dlp de fetch_title s'il tourne encore
        ytdlp = self._ytdlp_proc
        if ytdlp and ytdlp.poll() is None:
            try:
                ytdlp.terminate()
            except Exception:
                pass
        # 4. Fallback pkill côté host — tue tous les mpv-bin avec le titre pOpcOrn
        Updater.kill_all_mpv()
        try:
            os.remove(_MPV_IPC_SOCKET)
        except OSError:
            pass
        log_event("Player cleanup effectue.")

    def prefetch_cookies(self):
        """Export cookies en arrière-plan."""
        if self._cookie_prefetch_thread and self._cookie_prefetch_thread.is_alive():
            return
        self._cookie_prefetch_thread = threading.Thread(
            target=self.get_cookies, daemon=True
        )
        self._cookie_prefetch_thread.start()

    def prewarm_mpv(self):
        """Lance MPV en mode idle pour pré-charger le runtime Flatpak."""
        if self._prewarm_thread and self._prewarm_thread.is_alive():
            return
        self._prewarm_thread = threading.Thread(target=self._do_prewarm, daemon=True)
        self._prewarm_thread.start()

    def _do_prewarm(self):
        with self._play_lock:
            old_proc = self._mpv_idle_proc
            self._mpv_idle_proc = None
        if old_proc and old_proc.poll() is None:
            try:
                old_proc.terminate()
                old_proc.wait(timeout=2)
            except Exception:
                pass
            if old_proc.poll() is None:
                try:
                    old_proc.kill()
                except Exception:
                    pass
        # Tuer tout MPV orphelin côté host avant de lancer le nouveau idle
        # Seulement si aucune lecture en cours
        if not self._is_playing:
            Updater.kill_all_mpv()
            time.sleep(0.2)
        try:
            os.remove(_MPV_IPC_SOCKET)
        except OSError:
            pass

        proc = Updater.start_idle(
            _MPV_IPC_SOCKET,
            cookies_path=self.cookie_export_path,
            quality_target=self.quality_target,
            window_mode=self.window_mode,
            window_scale_percent=self.window_scale_percent,
        )
        with self._play_lock:
            self._mpv_idle_proc = proc

        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline:
            if os.path.exists(_MPV_IPC_SOCKET):
                log_event("MPV pre-warm: IPC socket pret.", level="debug")
                threading.Thread(target=self._watchdog, daemon=True).start()
                return
            time.sleep(0.1)
        log_event("MPV pre-warm: socket absent apres delai.", level="debug")

    def _watchdog(self):
        """Relance le prewarm si MPV idle meurt inopinement."""
        while True:
            time.sleep(10)
            if self._is_playing:
                continue
            with self._play_lock:
                proc = self._mpv_idle_proc
            if proc is None:
                return
            if proc.poll() is not None:
                log_event("MPV idle process termine, relance...", level="debug")
                self.prewarm_mpv()
                return

    # ─────────────────────────────
    # IPC
    # ─────────────────────────────

    def _ipc_command(self, *args):
        try:
            sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect(_MPV_IPC_SOCKET)
            msg = json.dumps({"command": list(args)}).encode() + b"\n"
            sock.sendall(msg)
            sock.close()
        except Exception:
            pass

    def _ipc_loadfile(self, url: str, start_pos: float = None) -> bool:
        """Send a loadfile command to the pre-warmed MPV via IPC socket."""
        try:
            sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect(_MPV_IPC_SOCKET)

            msg = json.dumps({
                "command": ["loadfile", url, "replace"],
                "request_id": 42
            }).encode() + b"\n"
            sock.sendall(msg)

            # Vérifier que MPV a accepté la commande
            buf = b""
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        # MPV a fermé la connexion en traitant la commande → succès
                        sock.close()
                        return True
                    buf += chunk
                    for line in buf.split(b"\n"):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            resp = json.loads(line)
                            if "event" in resp:
                                continue
                            if resp.get("request_id") == 42:
                                sock.close()
                                success = resp.get("error") == "success"
                                if not success:
                                    log_event(f"IPC loadfile erreur: {resp.get('error')}", level="debug")
                                return success
                        except Exception:
                            continue
                except OSError:
                    # Broken pipe = MPV a traité la commande → succès
                    return True
            sock.close()
        except Exception as exc:
            log_event(f"IPC loadfile echec: {exc}", level="debug")
        return False

    def _ipc_get_property(self, prop: str):
        try:
            sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
            sock.settimeout(1.5)
            sock.connect(_MPV_IPC_SOCKET)
            msg = json.dumps({
                "command": ["get_property", prop],
                "request_id": 1
            }).encode() + b"\n"
            sock.sendall(msg)
            buf = b""
            deadline = time.monotonic() + 1.5
            while time.monotonic() < deadline:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                    for line in buf.split(b"\n"):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            resp = json.loads(line)
                            # Ignorer les événements MPV asynchrones
                            if "event" in resp:
                                continue
                            if resp.get("request_id") == 1:
                                sock.close()
                                if resp.get("error") == "success":
                                    return resp.get("data")
                                return None
                        except Exception:
                            continue
                except OSError:
                    break
            sock.close()
        except Exception:
            pass
        return None

    def _fetch_title_async(self, url: str):
        """Récupère le titre via yt-dlp (sandbox) en arrière-plan."""
        import subprocess
        import json as _json
        try:
            log_event(f"fetch_title_async: start for {url}", level="debug")
            proc = subprocess.Popen(
                ["yt-dlp", "--no-playlist", "--skip-download",
                 "--dump-single-json", url],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self._ytdlp_proc = proc
            try:
                stdout, stderr = proc.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                log_event("fetch_title_async: timeout", level="debug")
                return
            finally:
                self._ytdlp_proc = None

            log_event(f"fetch_title_async: returncode={proc.returncode}", level="debug")
            if proc.returncode == 0 and stdout.strip():
                info = _json.loads(stdout.decode())
                title = info.get("title", "").strip()
                log_event(f"fetch_title_async: title='{title}'", level="debug")
                if title and hasattr(self, '_on_media_title'):
                    GLib.idle_add(self._on_media_title, url, title)
            else:
                log_event(f"fetch_title_async: stderr={stderr.decode()[:200]}", level="debug")
        except Exception as exc:
            log_event(f"fetch_title_async error: {exc}", level="debug")
            self._ytdlp_proc = None

    def _track_position(self, url: str, seek_to: float = None, hide_on_ready: bool = False):
        self._tracking = True
        self._tracked_pos = 0.0
        self._tracked_duration = None
        mpv_ready_signaled = False

        # Titre via yt-dlp en parallèle (non bloquant)
        threading.Thread(
            target=self._fetch_title_async, args=(url,), daemon=True
        ).start()

        log_event(f"track_position: debut pour {url}", level="debug")

        # Si reprise via IPC : attendre que MPV joue puis seek
        if seek_to and seek_to > 0:
            deadline = time.monotonic() + 15.0
            while time.monotonic() < deadline:
                pos = self._ipc_get_property("time-pos")
                if isinstance(pos, (int, float)) and pos >= 0:
                    self._ipc_command("seek", seek_to, "absolute")
                    log_event(f"track_position: seek to {seek_to:.1f}s", level="debug")
                    time.sleep(0.3)
                    break
                time.sleep(0.2)
        # Polling position/durée toutes les 5s via IPC
        had_valid_pos = False
        none_count = 0
        while self._tracking and self._is_playing:
            pos = self._ipc_get_property("time-pos")
            dur = self._ipc_get_property("duration")
            if isinstance(pos, (int, float)):
                self._tracked_pos = float(pos)
                had_valid_pos = True
                none_count = 0
                # Premier time-pos valide = MPV joue
                if not mpv_ready_signaled:
                    mpv_ready_signaled = True
                    self._stream_started = True
                    if hide_on_ready:
                        # Mode normal : cacher WebKit
                        GLib.idle_add(self._hide_for_mpv)
                    else:
                        # Mode commentaires : cacher seulement l'overlay, pas la fenêtre
                        if self.on_hide_loading:
                            GLib.idle_add(self.on_hide_loading)
            else:
                if had_valid_pos:
                    none_count += 1
                    if none_count >= 3:
                        # Vérifier si MPV est vraiment idle
                        # ou en train de charger la prochaine vidéo d'une playlist
                        idle = self._ipc_get_property("idle-active")
                        if idle is True or idle is None:
                            log_event("track_position: fin detectee via IPC", level="debug")
                            self._playback_ended.set()
                            break
                elif not had_valid_pos:
                    # Pas encore de lecture — MPV charge peut-être encore
                    # idle-active=True signifie que MPV a abandonné le flux
                    idle = self._ipc_get_property("idle-active")
                    if idle is True:
                        log_event("track_position: flux indisponible (idle sans lecture)", level="debug")
                        self._stream_started = False
                        self._playback_ended.set()
                        break
            if isinstance(dur, (int, float)) and dur > 0:
                self._tracked_duration = float(dur)
            log_event(f"track_position: pos={pos} dur={dur} tracked={self._tracked_pos:.1f}", level="debug")
            # Polling rapide si pos=None (détection fin de lecture), normal sinon
            time.sleep(1.0 if (had_valid_pos and not isinstance(pos, (int, float))) else 5.0)
        log_event(f"track_position: fin tracked_pos={self._tracked_pos:.1f} tracked_dur={self._tracked_duration}", level="debug")
        self._tracking = False

    def _wait_with_timeout(self, process, timeout: int = 43200) -> int:
        """Attend MPV avec un timeout de 12h max."""
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
    # SponsorBlock
    # ─────────────────────────────

    def _sync_sponsorblock(self):
        if not self.sponsorblock_script_path:
            return
        src_dir = os.path.dirname(self.sponsorblock_script_path)

        if self.sponsorblock_enabled:
            try:
                os.makedirs(_MPV_SCRIPTS_DIR, exist_ok=True)
                shared_dst = os.path.join(_MPV_SCRIPTS_DIR, "sponsorblock_shared")
                os.makedirs(shared_dst, exist_ok=True)
                shutil.copy2(self.sponsorblock_script_path,
                             os.path.join(_MPV_SCRIPTS_DIR, "sponsorblock.lua"))
                src_shared = os.path.join(src_dir, "sponsorblock_shared")
                for fname in ("main.lua", "sponsorblock.py"):
                    shutil.copy2(os.path.join(src_shared, fname),
                                 os.path.join(shared_dst, fname))
                log_event("SponsorBlock: fichiers installes.", level="debug")
            except Exception as exc:
                log_event(f"SponsorBlock: echec installation: {exc}", level="debug")
        else:
            try:
                lua = os.path.join(_MPV_SCRIPTS_DIR, "sponsorblock.lua")
                shared = os.path.join(_MPV_SCRIPTS_DIR, "sponsorblock_shared")
                if os.path.exists(lua):
                    os.remove(lua)
                if os.path.isdir(shared):
                    shutil.rmtree(shared)
                log_event("SponsorBlock: fichiers supprimes.", level="debug")
            except Exception as exc:
                log_event(f"SponsorBlock: echec suppression: {exc}", level="debug")

    # ─────────────────────────────
    # url normalization
    # ─────────────────────────────

    def _prepare_url(self, url: str) -> str:
        """Normalise une URL YouTube en supprimant les paramètres de tracking.
        Conserve uniquement v= (vidéo) et list= (playlist).
        """
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query, keep_blank_values=False)

            # youtu.be/VIDEO_ID → watch?v=VIDEO_ID
            if "youtu.be" in parsed.netloc:
                video_id = parsed.path.lstrip("/").split("?")[0]
                if video_id:
                    return f"https://www.youtube.com/watch?v={video_id}"
                return url

            # Playlist (hors mixes YouTube RD...)
            if "list" in params:
                playlist_id = params["list"][0]
                if not playlist_id.startswith("RD"):
                    return f"https://www.youtube.com/playlist?list={playlist_id}"

            # Vidéo simple — ne garder que v=
            if "v" in params:
                clean = urlencode({"v": params["v"][0]})
                return urlunparse(parsed._replace(
                    netloc="www.youtube.com", path="/watch", query=clean
                ))

        except Exception:
            pass

        return url

    def _get_monitor_offset(self) -> tuple[int, int]:
        try:
            surface = self.win.get_surface()
            if surface is None:
                return (0, 0)
            display = surface.get_display()
            monitor = display.get_monitor_at_surface(surface)
            if monitor is None:
                return (0, 0)
            rect = monitor.get_geometry()
            return (rect.x, rect.y)
        except Exception:
            return (0, 0)

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
        monitor_offset = self._get_monitor_offset()
        threading.Thread(target=self._launch, args=(url, monitor_offset), daemon=True).start()

    def update_playback_settings(
        self,
        quality_target: str,
        window_mode: str,
        window_scale_percent: int,
        sponsorblock_enabled: bool = False,
        audio_lang: str = "auto",
        subtitle_lang: str = "none",
        subtitle_fallback: bool = False,
    ):
        self.quality_target = quality_target
        self.window_mode = window_mode
        self.window_scale_percent = window_scale_percent
        self.sponsorblock_enabled = sponsorblock_enabled
        self.audio_lang = audio_lang
        self.subtitle_lang = subtitle_lang
        self.subtitle_fallback = subtitle_fallback
        self._sync_sponsorblock()
        if not self._is_playing:
            self.prewarm_mpv()

    # ─────────────────────────────
    # launch mpv
    # ─────────────────────────────

    def _launch(self, url: str, monitor_offset: tuple[int, int] = (0, 0)):
        cookies_path = None
        try:
            GLib.idle_add(self._show_loading)

            url = self._prepare_url(url)
            if self._cookie_prefetch_thread and self._cookie_prefetch_thread.is_alive():
                self._cookie_prefetch_thread.join()
            cookies_path = (
                self.cookie_export_path
                if os.path.exists(self.cookie_export_path)
                else self.get_cookies()
            )
            if not cookies_path:
                print("[BBS Popcorn] Cookie export failed, aborting MPV launch.")
                GLib.idle_add(self._hide_loading_only)
                return

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

            subs_active = self.subtitle_lang and self.subtitle_lang != "none"
            if idle_proc and not subs_active and self._ipc_loadfile(url, start_pos=start_pos):
                process = idle_proc
                used_ipc = True
                time.sleep(0.3)
            else:
                # Sous-titres demandés : tuer le MPV idle inutilisé, lancer un process dédié
                if idle_proc and subs_active:
                    try:
                        idle_proc.terminate()
                    except Exception:
                        pass
                process = self._start_process(
                    url, cookies_path,
                    use_fallback_format=False,
                    start_pos=start_pos,
                    ipc_socket_path=_MPV_IPC_SOCKET,
                    monitor_offset=monitor_offset,
                )
                used_ipc = False

            if process.poll() is not None:
                if self._retry_with_fallback(url, cookies_path, monitor_offset):
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
            # Ne pas cacher WebKit maintenant — _track_position le fera
            # quand MPV joue réellement (premier time-pos valide)
            self._playback_ended.clear()
            self._stream_started = False
            threading.Thread(
                target=self._track_position, args=(url, start_pos, True), daemon=True
            ).start()

            if used_ipc:
                # Prewarm MPV reste en idle après la lecture → attendre _playback_ended
                self._playback_ended.wait(timeout=43200)
                return_code = 0
            else:
                return_code = self._wait_with_timeout(process)

            self._tracking = False

            # Flux jamais démarré → vidéo à venir ou indisponible
            if not self._stream_started:
                log_event(f"Flux non demarré pour {url}")
                self._status("Vidéo indisponible.")
                notice = Updater.get_upcoming_live_message(url)
                if notice and self.on_show_notice:
                    GLib.idle_add(self.on_show_notice, notice)
                else:
                    GLib.idle_add(self._hide_loading_only)
                GLib.idle_add(self._show_after_mpv)
                return

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
        monitor_offset: tuple[int, int] = (0, 0),
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
            monitor_offset=monitor_offset,
            audio_lang=self.audio_lang,
            subtitle_lang=self.subtitle_lang,
            subtitle_fallback=self.subtitle_fallback,
        )

    def _retry_with_fallback(
        self, url: str, cookies_path: str,
        monitor_offset: tuple[int, int] = (0, 0)
    ) -> bool:
        self._status("Format compatible: nouvelle tentative...")
        process = self._start_process(
            url, cookies_path,
            use_fallback_format=True,
            ipc_socket_path=_MPV_IPC_SOCKET,
            monitor_offset=monitor_offset,
        )
        time.sleep(0.5)
        if process.poll() is not None:
            return False
        self._status("Lecture en cours (mode compatible).")
        threading.Thread(
            target=self._track_position, args=(url, start_pos, True), daemon=True
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
