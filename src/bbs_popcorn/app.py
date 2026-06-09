import os
import threading
import json
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")

from gi.repository import Gtk, WebKit, GLib, Gio

from bbs_popcorn.history_store import HistoryStore
from bbs_popcorn.i18n import t, set_lang
from bbs_popcorn import cast_manager
from bbs_popcorn.logging_utils import log_event
from bbs_popcorn.player import MpvPlayer


YOUTUBE_URL = "https://www.youtube.com"


def format_timestamp(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"


SETTINGS_FILE = os.path.join(
    GLib.get_user_config_dir(), "bbs-popcorn", "settings.json"
)


# ─────────────────────────────
# Settings
# ─────────────────────────────

def load_settings() -> dict:
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    defaults = {
        "theme": "auto",
        "playback_profile": "gaming",
        "quality_target": "1080",
        "window_mode": "windowed",
        "window_scale_percent": 80,
        "sponsorblock_enabled": False,
        "webkit_mode": "normal",
        "language": "fr",
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                settings = defaults.copy()
                settings.update(loaded)
                if settings.get("playback_profile") not in {"gaming", "quality"}:
                    settings["playback_profile"] = "gaming"
                if settings.get("quality_target") not in {"2160", "1440", "1080", "720", "480"}:
                    settings["quality_target"] = "1080"
                if settings.get("window_mode") not in {"fullscreen", "windowed"}:
                    settings["window_mode"] = "windowed"
                if settings.get("webkit_mode") not in {"normal", "eco"}:
                    settings["webkit_mode"] = "normal"
                try:
                    scale = int(settings.get("window_scale_percent", 80))
                except Exception:
                    scale = 80
                settings["window_scale_percent"] = max(50, min(100, scale))
                return settings
        except Exception:
            pass
    return defaults


def save_settings(settings: dict):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)


# ─────────────────────────────
# App
# ─────────────────────────────

class YtMpvApp(Gtk.Application):

    def __init__(self, cookie_db_path: str, cookie_export_path: str,
                 sponsorblock_script_path: str = None):
        super().__init__(
            application_id="io.github.blacksamdev.Popcorn",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )
        self.connect("activate", self.on_activate)
        self.cookie_db_path = cookie_db_path
        self.cookie_export_path = cookie_export_path
        self.sponsorblock_script_path = sponsorblock_script_path
        self.settings = load_settings()
        self.history = HistoryStore()
        self._window_created = False
        set_lang(self.settings.get("language", "fr"))

    # ───────────── Activation ─────────────

    def on_activate(self, app):
        # Instance unique — si la fenêtre existe déjà, la ramener au premier plan
        if self._window_created:
            self.win.present()
            return
        self._window_created = True
        self._harden_cookie_paths()
        self.win = Gtk.ApplicationWindow(application=app)
        self.win.set_title("BBS Popcorn")
        self.win.set_default_size(1280, 800)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # ───────── Navigation ─────────
        navbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        btn_back    = Gtk.Button(label="◀")
        btn_forward = Gtk.Button(label="▶")
        btn_reload  = Gtk.Button(label="↺")
        btn_home    = Gtk.Button(label="⌂")

        self.url_bar = Gtk.Entry()
        self.url_bar.set_hexpand(True)
        self.url_bar.set_text(YOUTUBE_URL)
        self.url_bar.set_editable(True)
        self.url_bar.set_can_focus(True)
        self.url_bar.connect("activate", self._on_url_bar_activate)

        self.btn_history = Gtk.MenuButton(label="🕐")
        self.btn_history.set_tooltip_text(t("tooltip_history"))

        self._current_video_url = None
        self._comments_nav = False
        self._cast_device = None
        self._cast_daemon = cast_manager.CastDaemon()
        self._cast_paused = False

        btn_settings = Gtk.MenuButton(label="⚙")
        btn_settings.set_popover(self._build_settings_popover())

        self.btn_comments = Gtk.Button(label="💬")
        self.btn_comments.set_tooltip_text(t("tooltip_comments"))
        self.btn_comments.set_sensitive(False)
        self.btn_comments.connect("clicked", self._on_comments_clicked)

        self.btn_cast = Gtk.Button(label="📺")
        self.btn_cast.set_tooltip_text("Caster sur un Chromecast")
        self.btn_cast.set_sensitive(True)
        self.btn_cast.connect("clicked", self._on_cast_clicked)

        navbar.append(btn_back)
        navbar.append(btn_forward)
        navbar.append(btn_reload)
        navbar.append(btn_home)
        navbar.append(self.url_bar)
        navbar.append(self.btn_history)
        navbar.append(self.btn_comments)
        navbar.append(self.btn_cast)
        navbar.append(btn_settings)

        # ───────── WebKit bridge ─────────
        self.content_manager = WebKit.UserContentManager()
        self.content_manager.register_script_message_handler("bbspopcorn")
        self.content_manager.connect(
            "script-message-received::bbspopcorn", self.on_js_message
        )

        # ───────── WebView ─────────
        self.webview = WebKit.WebView(user_content_manager=self.content_manager)

        network_session = self.webview.get_network_session()
        cookie_manager = network_session.get_cookie_manager()
        cookie_manager.set_persistent_storage(
            self.cookie_db_path, WebKit.CookiePersistentStorage.SQLITE
        )
        cookie_manager.set_accept_policy(WebKit.CookieAcceptPolicy.NO_THIRD_PARTY)

        ws = self.webview.get_settings()
        ws.set_enable_javascript(True)
        ws.set_enable_media(True)
        ws.set_enable_html5_local_storage(True)
        ws.set_media_playback_requires_user_gesture(False)
        ws.set_user_agent(
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120 Safari/537.36"
        )
        # Toujours désactivé dans les deux modes
        ws.set_enable_media_stream(False)
        try:
            ws.set_enable_encrypted_media(False)
        except Exception:
            pass

        self._apply_webkit_settings()

        self.webview.set_vexpand(True)
        self.webview.load_uri(YOUTUBE_URL)

        btn_back.connect("clicked",   lambda _: self.webview.go_back())
        btn_forward.connect("clicked", lambda _: self.webview.go_forward())
        btn_reload.connect("clicked",  lambda _: self.webview.reload())
        btn_home.connect("clicked",    lambda _: self.webview.load_uri(YOUTUBE_URL))

        self.webview.connect("load-changed", self.on_load_changed)
        self.webview.connect("decide-policy", self.on_decide_policy)

        vbox.append(navbar)
        self.content_overlay = Gtk.Overlay()
        self.content_overlay.set_child(self.webview)

        # ───────── Loading overlay ─────────
        loading_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        loading_box.set_halign(Gtk.Align.CENTER)
        loading_box.set_valign(Gtk.Align.CENTER)
        loading_box.add_css_class("loading-overlay")

        self.loading_spinner = Gtk.Spinner()
        self.loading_spinner.set_size_request(64, 64)
        loading_box.append(self.loading_spinner)
        self.loading_label = Gtk.Label(label=t("loading"))
        loading_box.append(self.loading_label)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            .loading-overlay {
                background-color: rgba(34, 38, 43, 0.92);
                border-radius: 12px;
                padding: 18px 22px;
            }
            .loading-overlay label { color: #d7dde5; font-size: 1.05em; }
            .status-bar { background-color: rgba(34, 38, 43, 0.85); padding: 4px 10px; }
            .status-bar label { color: #d7dde5; }
        """)
        Gtk.StyleContext.add_provider_for_display(
            self.win.get_display(), css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.loading_revealer = Gtk.Revealer()
        self.loading_revealer.set_transition_type(Gtk.RevealerTransitionType.CROSSFADE)
        self.loading_revealer.set_reveal_child(False)
        self.loading_revealer.set_can_target(False)
        self.loading_revealer.set_child(loading_box)
        self.content_overlay.add_overlay(self.loading_revealer)
        vbox.append(self.content_overlay)

        # Barre cast
        self._cast_revealer = Gtk.Revealer()
        self._cast_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self._cast_revealer.set_transition_duration(200)
        cast_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        cast_bar.set_margin_start(8); cast_bar.set_margin_end(8)
        cast_bar.set_margin_top(4); cast_bar.set_margin_bottom(4)
        self._cast_bar_label = Gtk.Label(label="")
        self._cast_bar_label.set_hexpand(True)
        self._cast_bar_label.set_xalign(0)
        cast_bar.append(self._cast_bar_label)
        self._btn_cast_pause = Gtk.Button(label="▌▌")
        self._btn_cast_pause.set_tooltip_text("Pause / Lecture")
        self._btn_cast_pause.connect("clicked", self._on_cast_pause_clicked)
        cast_bar.append(self._btn_cast_pause)
        btn_vol_down = Gtk.Button(label="🔈")
        btn_vol_down.set_tooltip_text("Volume -")
        btn_vol_down.connect("clicked", lambda b: self._cast_daemon.vol_down())
        cast_bar.append(btn_vol_down)
        btn_vol_up = Gtk.Button(label="🔊")
        btn_vol_up.set_tooltip_text("Volume +")
        btn_vol_up.connect("clicked", lambda b: self._cast_daemon.vol_up())
        cast_bar.append(btn_vol_up)
        btn_cast_release = Gtk.Button(label="✕")
        btn_cast_release.set_tooltip_text("Liberer le peripherique")
        btn_cast_release.connect("clicked", self._on_cast_release)
        cast_bar.append(btn_cast_release)
        self._cast_revealer.set_child(cast_bar)
        vbox.append(self._cast_revealer)

        # ───────── Statusbar ─────────
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        status_box.add_css_class("status-bar")
        self.status_label = Gtk.Label(label=t("status_ready"))
        self.status_label.set_halign(Gtk.Align.START)
        status_box.append(self.status_label)
        vbox.append(status_box)

        self.win.set_child(vbox)
        self.win.connect("close-request", self._on_close_request)
        self.win.connect("destroy", self._on_shutdown)

        # Fermer les popovers au clic dans la fenêtre — phase CAPTURE avant WebKit
        click = Gtk.GestureClick()
        click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        click.connect("pressed", self._on_window_click)
        self.webview.add_controller(click)

        self.win.present()

        # ───────── Player ─────────
        self.player = MpvPlayer(
            self.cookie_db_path, self.cookie_export_path, self.win,
            playback_profile=self.settings.get("playback_profile", "gaming"),
            sponsorblock_script_path=self.sponsorblock_script_path,
        )
        self.player.on_show_loading  = self._show_loading_overlay
        self.player.on_hide_loading  = self._hide_loading_overlay
        self.player.on_show_notice   = self._show_loading_notice
        self.player.on_status_change = self._set_status
        self.player._on_media_title  = self._update_history_title

        self._apply_player_settings()
        self.player.prefetch_cookies()
        self.player.prewarm_mpv()
        self.btn_history.set_popover(self._build_history_popover())
        threading.Thread(target=self._check_dependencies, daemon=True).start()

    # ───────── WebKit mode ─────────

    def _apply_webkit_settings(self):
        """Applique les options WebKit selon le mode normal/éco."""
        ws = self.webview.get_settings()
        eco = (self.settings.get("webkit_mode", "normal") == "eco")
        try:
            ws.set_enable_webgl(not eco)
        except Exception:
            pass
        try:
            ws.set_enable_webaudio(not eco)
        except Exception:
            pass
        try:
            policy = (WebKit.HardwareAccelerationPolicy.ON_DEMAND if eco
                      else WebKit.HardwareAccelerationPolicy.ALWAYS)
            ws.set_hardware_acceleration_policy(policy)
        except Exception:
            pass

    # ───────── Misc helpers ─────────

    def _harden_cookie_paths(self):
        state_dir = os.path.dirname(self.cookie_db_path)
        os.makedirs(state_dir, mode=0o700, exist_ok=True)
        try:
            os.chmod(state_dir, 0o700)
        except OSError:
            pass
        for path in (self.cookie_db_path, self.cookie_export_path):
            if os.path.exists(path):
                try:
                    os.chmod(path, 0o600)
                except OSError:
                    pass

    def _check_dependencies(self):
        from bbs_popcorn.updater import Updater
        status = Updater.status()
        missing = []
        if not status.get("mpv", False):
            missing.append("MPV Flatpak manquant : flatpak install flathub io.mpv.Mpv")
        if not status.get("yt-dlp", False):
            missing.append("yt-dlp manquant dans l'application")
        if missing:
            msg = " | ".join(missing)
            log_event(f"Dependances manquantes: {msg}")
            GLib.idle_add(self._set_status, msg)

    def _update_history_title(self, url: str, title: str):
        if title and url:
            self.history.add(url, title=title)
            # Rafraîchir le popover s'il est visible
            if hasattr(self, '_history_popover') and self._history_popover.get_visible():
                self._refresh_history_list()
        return False

    # ───────── Navigation ─────────

    def _on_comments_clicked(self, _btn):
        if not self._current_video_url:
            return
        self._comments_nav = True
        self.webview.load_uri(self._current_video_url)

    def on_load_changed(self, webview, event):
        if event == WebKit.LoadEvent.COMMITTED:
            self.url_bar.set_text(webview.get_uri())
        if event == WebKit.LoadEvent.FINISHED:
            self.inject_interceptor()
            if self._comments_nav and "/watch" in (webview.get_uri() or ""):
                self._comments_nav = False
                self._inject_comments_css()

    def on_decide_policy(self, webview, decision, decision_type):
        if decision_type != WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            return False
        action = decision.get_navigation_action()
        if not action:
            return False
        # Navigations programmatiques (depuis le code Python) toujours autorisées
        nav_type = action.get_navigation_type()
        if nav_type == WebKit.NavigationType.OTHER:
            return False
        request = action.get_request()
        if not request:
            return False
        uri = request.get_uri() or ""
        if self._is_allowed_uri(uri):
            return False
        decision.ignore()
        self._set_status(t("status_blocked"))
        return True

    def _is_allowed_uri(self, uri: str) -> bool:
        return uri.startswith((
            "https://www.youtube.com", "https://youtube.com",
            "https://m.youtube.com", "https://youtu.be", "about:blank",
        ))

    # ───────── JS injection ─────────

    def inject_interceptor(self):
        eco = "true" if self.settings.get("webkit_mode", "normal") == "eco" else "false"
        js = f"""
        (function () {{
            if (window.__bbsPopcornIntercept) {{
                document.removeEventListener('click', window.__bbsPopcornIntercept, true);
            }}
            const ECO_MODE = {eco};

            function disableSpeechApis() {{
                try {{
                    if (window.speechSynthesis) {{
                        window.speechSynthesis.cancel();
                        window.speechSynthesis.speak = function () {{}};
                    }}
                }} catch (_) {{}}
                try {{
                    window.SpeechRecognition = undefined;
                    window.webkitSpeechRecognition = undefined;
                }} catch (_) {{}}
            }}

            function forceShortsAudio() {{
                if (ECO_MODE) return;
                if (!location.pathname.includes('/shorts/')) return;
                const enableAudio = () => {{
                    const v = document.querySelector('video');
                    if (!v) return;
                    v.muted = false;
                    if (v.volume === 0) v.volume = 1;
                    if (v.paused) v.play().catch(() => {{}});
                }};
                const muteSec = () => {{
                    const main = document.querySelector('video');
                    document.querySelectorAll('audio, video').forEach(n => {{
                        if (n !== main) {{ n.muted = true; n.volume = 0; }}
                    }});
                }};
                enableAudio(); muteSec();
                setTimeout(() => {{ enableAudio(); muteSec(); }}, 300);
                new MutationObserver(() => {{ enableAudio(); muteSec(); }})
                    .observe(document.body, {{childList: true, subtree: true}});
                document.addEventListener("yt-navigate-finish",
                    () => {{ enableAudio(); muteSec(); }}, true);
            }}

            window.__bbsPopcornIntercept = function(e) {{
                const a = e.target.closest('a[href]');
                if (!a) return;
                const href = a.href;

                // Vidéo à venir → laisser YouTube gérer
                const container = a.closest(
                    'ytd-rich-item-renderer, ytd-video-renderer, ' +
                    'ytd-compact-video-renderer, ytd-grid-video-renderer'
                );
                if (container) {{
                    const upcoming = container.querySelector(
                        '[data-style="UPCOMING"], [overlay-style="UPCOMING"]'
                    );
                    if (upcoming) return;
                }}

                // Mode éco : Shorts → MPV
                if (ECO_MODE && href.includes('youtube.com/shorts/')) {{
                    const m = href.match(/shorts[/]([a-zA-Z0-9_-]+)/);
                    if (m) {{
                        e.preventDefault();
                        e.stopPropagation();
                        window.webkit.messageHandlers.bbspopcorn.postMessage(
                            'https://www.youtube.com/watch?v=' + m[1]
                        );
                    }}
                    return;
                }}

                if (href.includes('youtube.com/watch') ||
                    href.includes('youtube.com/playlist')) {{
                    e.preventDefault();
                    e.stopPropagation();
                    window.webkit.messageHandlers.bbspopcorn.postMessage(href);
                }}
            }};

            document.addEventListener('click', window.__bbsPopcornIntercept, true);
            disableSpeechApis();
            forceShortsAudio();
        }})();
        """
        self.webview.evaluate_javascript(js, -1, None, None, None, None, None)

    # ───────── JS messages ─────────

    def _inject_comments_css(self):
        """Cache le player YouTube et empêche toute lecture — ne laisse que les commentaires."""
        js = """
        (function() {
            // Cacher le player et couper tout audio
            const style = document.createElement('style');
            style.textContent = `
                ytd-player, #movie_player, #player-container-outer,
                #player-container, ytd-masthead { }
                ytd-player, #movie_player { display: none !important; }
            `;
            document.head.appendChild(style);

            // Couper toutes les vidéos
            function muteAll() {
                document.querySelectorAll('video, audio').forEach(v => {
                    v.pause(); v.muted = true; v.autoplay = false;
                    v.play = () => Promise.resolve();
                });
            }
            muteAll();
            new MutationObserver(muteAll)
                .observe(document.body, {childList: true, subtree: true});
        })();
        """
        self.webview.evaluate_javascript(js, -1, None, None, None, None, None)

    def on_js_message(self, manager, message):
        url = message.to_string()
        normalized = self.player._prepare_url(url)
        print(f"[BBS Popcorn] Play: {url}")
        log_event(f"Play request: {url}")
        self.history.add(normalized, title="")
        resume_pos = self.player._resume.get(normalized)
        if resume_pos:
            self._set_status(t("status_resume", time=format_timestamp(resume_pos)))
        # Tracker l'URL pour le bouton commentaires
        if "watch?v=" in normalized:
            self._current_video_url = normalized
            GLib.idle_add(lambda: self.btn_comments.set_sensitive(True) or False)
        if self._cast_device:
            self._cast_video(url)
            return
        self.player.play(url)

    def _on_url_bar_activate(self, entry):
        url = entry.get_text().strip()
        if not url:
            return
        if not url.startswith("http"):
            url = "https://" + url
        if ("youtube.com/watch" in url or "youtube.com/playlist" in url
                or "youtu.be/" in url):
            normalized = self.player._prepare_url(url)
            log_event(f"Play request (url bar): {url}")
            self.history.add(normalized, title="")
            resume_pos = self.player._resume.get(normalized)
            if resume_pos:
                self._set_status(t("status_resume", time=format_timestamp(resume_pos)))
            self.player.play(url)
        else:
            self.webview.load_uri(url)

    def _on_cast_clicked(self, _btn):
        self._show_cast_popover()

    def _cast_video(self, url):
        normalized = self.player._prepare_url(url)
        self.history.add(normalized, title="")
        device = self._cast_device
        self._set_status("Cast : resolution du flux...")
        def _resolve():
            stream_url = cast_manager.resolve_stream_url(normalized)
            if not stream_url:
                GLib.idle_add(self._set_status, "Impossible de resoudre le flux.")
                return
            GLib.idle_add(self._set_status, "Cast vers " + device["name"] + "...")
            self._cast_daemon.cast_async(
                stream_url,
                callback=lambda ok, err: GLib.idle_add(
                    self._set_status,
                    "Lecture sur " + device["name"] + " !" if ok else "Erreur cast : " + err
                )
            )
        threading.Thread(target=_resolve, daemon=True).start()

    def _show_cast_popover(self):
        popover = Gtk.Popover()
        popover.set_autohide(True)
        popover.set_parent(self.btn_cast)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(8); box.set_margin_bottom(8)
        box.set_margin_start(12); box.set_margin_end(12)
        # Header
        lbl_title = Gtk.Label(label="Sortie video :")
        lbl_title.set_xalign(0)
        box.append(lbl_title)
        # Cet appareil
        active = self._cast_device

        spinner = Gtk.Spinner()
        spinner.start()
        lbl_search = Gtk.Label(label="Recherche...")
        box.append(spinner)
        box.append(lbl_search)
        popover.set_child(box)
        popover.popup()
        cast_manager.discover_async(
            lambda d, e: GLib.idle_add(
                self._update_cast_popover, popover, box, spinner, lbl_search, d, e
            )
        )

    def _update_cast_popover(self, popover, box, spinner, lbl_search, devices, error):
        spinner.stop()
        spinner.set_visible(False)
        lbl_search.set_visible(False)
        active = self._cast_device
        if error == "missing":
            lbl = Gtk.Label(label="pychromecast manquant sur le host.")
            box.append(lbl)
            lbl2 = Gtk.Label(label="pip install pychromecast")
            box.append(lbl2)
        elif not devices:
            lbl = Gtk.Label(label="Aucun Chromecast trouve.")
            box.append(lbl)
        else:
            for device in devices:
                name = device["name"]
                model = device["model"]
                is_active = active and active.get("host") == device.get("host")
                prefix = "\u2713  " if is_active else "   "
                btn = Gtk.Button(label="\U0001f4fa " + prefix + name + "  \u2014  " + model)
                btn.connect("clicked", self._on_cast_to_device, device, popover)
                box.append(btn)
        return False

    def _on_cast_select_local(self, _btn, popover):
        popover.popdown()
        device = self._cast_device
        self._cast_device = None
        self._cast_daemon = cast_manager.CastDaemon()
        self._cast_paused = False
        self.btn_cast.set_tooltip_text("Caster sur un Chromecast")
        self._set_status("Arret du cast...")
        if device:
            self._cast_daemon.stop()
        self._cast_daemon.quit()
        self._cast_daemon = cast_manager.CastDaemon()
        self._cast_paused = False

    def _on_cast_pause_clicked(self, _btn):
        if self._cast_paused:
            self._cast_daemon.resume()
            self._btn_cast_pause.set_label("▌▌")
            self._cast_paused = False
        else:
            self._cast_daemon.pause()
            self._btn_cast_pause.set_label("▶")
            self._cast_paused = True

    def _on_cast_release(self, _btn):
        self._cast_device = None
        self._cast_paused = False
        self._btn_cast_pause.set_label("▌▌")
        self.btn_cast.set_tooltip_text("Caster sur un Chromecast")
        self._cast_revealer.set_reveal_child(False)
        self._set_status("Sortie video : BBS pOpcOrn (MPV).")
        self._cast_daemon.stop()
        self._cast_daemon.quit()
        self._cast_daemon = cast_manager.CastDaemon()

    def _on_cast_to_device(self, _btn, device, popover):
        popover.popdown()
        self._cast_device = device
        self._cast_paused = False
        self._btn_cast_pause.set_label("▌▌")
        self.btn_cast.set_tooltip_text("Sortie video : " + device["name"])
        self._cast_bar_label.set_label("📺  " + device["name"] + "  —  prochaine vidéo castée")
        self._cast_revealer.set_reveal_child(True)
        self._set_status("Mode cast : " + device["name"] + ".")
        def _on_daemon_ready(ok, err):
            if ok:
                self._cast_daemon.splash()
            else:
                GLib.idle_add(self._set_status, "Cast : " + (err or "erreur connexion"))
        self._cast_daemon.start_async(device["host"], callback=lambda ok, e: GLib.idle_add(_on_daemon_ready, ok, e))

    def _on_window_click(self, gesture, n_press, x, y):

        if hasattr(self, '_settings_popover') and self._settings_popover.get_visible():
            self._settings_popover.popdown()
        if hasattr(self, '_history_popover') and self._history_popover.get_visible():
            self._history_popover.popdown()

    def _on_close_request(self, _win):
        if self._cast_daemon.is_running():
            self._cast_daemon.quit()
        self.player.cleanup()
        self.quit()
        return False

    def _on_shutdown(self, _win):
        self.player.cleanup()
        self.quit()

    # ───────── Loading overlay ─────────

    def _show_loading_overlay(self):
        self.loading_label.set_text(t("loading"))
        self.loading_revealer.set_can_target(True)
        self.loading_spinner.start()
        self.loading_revealer.set_reveal_child(True)

    def _hide_loading_overlay(self):
        self.loading_revealer.set_reveal_child(False)
        self.loading_spinner.stop()
        self.loading_revealer.set_can_target(False)

    def _show_loading_notice(self, message: str):
        self.loading_label.set_text(message)
        self.loading_spinner.stop()
        self.loading_revealer.set_can_target(False)
        self.loading_revealer.set_reveal_child(True)
        GLib.timeout_add(3000, self._hide_notice_overlay)
        return False

    def _hide_notice_overlay(self):
        self._hide_loading_overlay()
        return False

    def _set_status(self, message: str):
        self.status_label.set_text(message)
        return False

    # ───────── History popover ─────────

    def _build_history_popover(self):
        popover = Gtk.Popover()
        popover.set_autohide(True)
        self._history_popover = popover
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(8); box.set_margin_bottom(8)
        box.set_margin_start(10); box.set_margin_end(10)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title_label = Gtk.Label(label=t("tooltip_history"))
        title_label.set_hexpand(True); title_label.set_xalign(0)
        btn_clear = Gtk.Button(label=t("history_clear"))
        btn_clear.connect("clicked", self._on_history_clear)
        header.append(title_label); header.append(btn_clear)
        box.append(header)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(200); scrolled.set_max_content_height(400)
        scrolled.set_min_content_width(360)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._history_list_box = Gtk.ListBox()
        self._history_list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._refresh_history_list()
        scrolled.set_child(self._history_list_box)
        box.append(scrolled)

        popover.set_child(box)
        popover.connect("show", lambda _: self._refresh_history_list())
        return popover

    def _refresh_history_list(self):
        while child := self._history_list_box.get_first_child():
            self._history_list_box.remove(child)
        entries = self.history.entries()
        if not entries:
            lbl = Gtk.Label(label=t("history_empty"))
            lbl.set_margin_top(8); lbl.set_margin_bottom(8)
            self._history_list_box.append(lbl)
            return
        for entry in entries:
            url   = entry.get("url", "")
            title = entry.get("title", url)
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            row_box.set_margin_top(4); row_box.set_margin_bottom(4)
            lbl = Gtk.Label(label=title[:60] + ("…" if len(title) > 60 else ""))
            lbl.set_hexpand(True); lbl.set_xalign(0)
            lbl.set_tooltip_text(url)
            row_box.append(lbl)
            btn = Gtk.Button(label="▶")
            btn.connect("clicked", self._on_history_play, url)
            row_box.append(btn)
            self._history_list_box.append(row_box)

    def _on_history_play(self, _btn, url):
        self._history_popover.popdown()
        resume_pos = self.player._resume.get(url)
        if resume_pos:
            self._set_status(t("status_resume", time=format_timestamp(resume_pos)))
        if self._cast_device:
            self._cast_video(url)
        else:
            self.player.play(url)

    def _on_history_clear(self, _btn):
        self.history.clear()
        self._refresh_history_list()

    # ───────── Settings popover ─────────

    def _build_settings_popover(self):
        self.pending_settings = dict(self.settings)
        popover = Gtk.Popover()
        popover.set_autohide(True)
        self._settings_popover = popover
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(8); box.set_margin_bottom(8)
        box.set_margin_start(10); box.set_margin_end(10)

        # ── Langue (en premier pour les anglophones) ──
        lang_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lang_label = Gtk.Label(label=t("settings_language"))
        lang_label.set_xalign(0); lang_label.set_hexpand(True)
        lang_row.append(lang_label)
        self.lang_combo = Gtk.ComboBoxText()
        self.lang_combo.append("fr", "Français")
        self.lang_combo.append("en", "English")
        self.lang_combo.set_active_id(self.pending_settings.get("language", "fr"))
        self.lang_combo.connect("changed", self._on_lang_changed)
        lang_row.append(self.lang_combo)
        box.append(lang_row)

        self.lang_restart_label = Gtk.Label(label="")
        self.lang_restart_label.set_xalign(0)
        self.lang_restart_label.set_visible(False)
        self.lang_restart_label.get_style_context().add_class("dim-label")
        box.append(self.lang_restart_label)

        box.append(Gtk.Separator())

        # ── Qualité ──
        quality_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        quality_row.append(Gtk.Label(label=t("settings_quality")))
        self.quality_combo = Gtk.ComboBoxText()
        for q in ["2160", "1440", "1080", "720", "480"]:
            self.quality_combo.append_text(q)
        self.quality_combo.set_active(
            ["2160", "1440", "1080", "720", "480"].index(
                self.pending_settings["quality_target"]
            )
        )
        self.quality_combo.connect("changed", self._on_settings_changed)
        quality_row.append(self.quality_combo)
        box.append(quality_row)

        # ── Mode fenêtre ──
        mode_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        mode_row.append(Gtk.Label(label=t("settings_window")))
        self.mode_combo = Gtk.ComboBoxText()
        self.mode_combo.append("windowed",   t("settings_window_w"))
        self.mode_combo.append("fullscreen", t("settings_window_fs"))
        self.mode_combo.set_active_id(self.pending_settings["window_mode"])
        self.mode_combo.connect("changed", self._on_settings_changed)
        mode_row.append(self.mode_combo)
        box.append(mode_row)

        # ── Taille ──
        scale_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.scale_label = Gtk.Label(
            label=t("settings_size", value=self.pending_settings['window_scale_percent'])
        )
        self.scale_label.set_xalign(0)
        scale_row.append(self.scale_label)
        self.scale_adjustment = Gtk.Adjustment(
            value=float(self.pending_settings["window_scale_percent"]),
            lower=50.0, upper=100.0,
            step_increment=5.0, page_increment=10.0, page_size=0.0
        )
        self.scale_slider = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=self.scale_adjustment
        )
        self.scale_slider.set_draw_value(False)
        self.scale_slider.connect("value-changed", self._on_scale_changed)
        scale_row.append(self.scale_slider)
        self.scale_spin = Gtk.SpinButton(
            adjustment=self.scale_adjustment, climb_rate=1.0, digits=0
        )
        self.scale_spin.set_numeric(True)
        self.scale_spin.connect("value-changed", self._on_scale_changed)
        scale_row.append(self.scale_spin)
        box.append(scale_row)

        # ── SponsorBlock ──
        sb_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        sb_label = Gtk.Label(label=t("settings_sponsorblock"))
        sb_label.set_xalign(0); sb_label.set_hexpand(True)
        sb_row.append(sb_label)
        self.sponsorblock_switch = Gtk.Switch()
        self.sponsorblock_switch.set_active(
            self.pending_settings.get("sponsorblock_enabled", False)
        )
        self.sponsorblock_switch.connect("state-set", self._on_sponsorblock_changed)
        if not self.sponsorblock_script_path:
            self.sponsorblock_switch.set_sensitive(False)
            sb_label.set_tooltip_text(t("settings_sb_na"))
        sb_row.append(self.sponsorblock_switch)
        box.append(sb_row)

        # ── Mode WebKit ──
        wk_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        wk_label = Gtk.Label(label=t("settings_webkit"))
        wk_label.set_xalign(0); wk_label.set_hexpand(True)
        wk_row.append(wk_label)
        self.webkit_mode_combo = Gtk.ComboBoxText()
        self.webkit_mode_combo.append("normal", t("settings_webkit_n"))
        self.webkit_mode_combo.append("eco",    t("settings_webkit_eco"))
        self.webkit_mode_combo.set_active_id(
            self.pending_settings.get("webkit_mode", "normal")
        )
        self.webkit_mode_combo.connect("changed", self._on_settings_changed)
        wk_row.append(self.webkit_mode_combo)
        btn_help = Gtk.Button(label="?")
        btn_help.set_tooltip_text(t("settings_eco_tooltip"))
        btn_help.set_sensitive(False)
        wk_row.append(btn_help)
        box.append(wk_row)

        # ── Aide ──
        help_label = Gtk.Label(label=t("settings_help"))
        help_label.set_xalign(0); help_label.set_wrap(True)
        help_label.set_max_width_chars(36)
        box.append(help_label)

        popover.set_child(box)
        self._sync_scale_sensitivity()
        return popover

    def _apply_player_settings(self):
        self.player.update_playback_settings(
            quality_target=self.settings.get("quality_target", "1080"),
            window_mode=self.settings.get("window_mode", "windowed"),
            window_scale_percent=int(self.settings.get("window_scale_percent", 80)),
            sponsorblock_enabled=bool(self.settings.get("sponsorblock_enabled", False)),
        )

    def _auto_save(self):
        """Sauvegarde immédiate sans fermer le popover."""
        self.settings.update(self.pending_settings)
        save_settings(self.settings)
        self._apply_player_settings()
        self._apply_webkit_settings()
        self.inject_interceptor()

    def _on_sponsorblock_changed(self, switch, state):
        self.pending_settings["sponsorblock_enabled"] = state
        self._auto_save()

    def _on_scale_changed(self, scale):
        value = int(scale.get_value())
        self.scale_label.set_text(t("settings_size", value=value))
        self.pending_settings["window_scale_percent"] = value
        self._auto_save()

    def _on_settings_changed(self, *_args):
        self.pending_settings["quality_target"] = (
            self.quality_combo.get_active_text() or "1080"
        )
        self.pending_settings["window_mode"] = (
            self.mode_combo.get_active_id() or "windowed"
        )
        self.pending_settings["webkit_mode"] = (
            self.webkit_mode_combo.get_active_id() or "normal"
        )
        self._sync_scale_sensitivity()
        self._auto_save()

    def _on_lang_changed(self, combo):
        selected = combo.get_active_id() or "fr"
        self.pending_settings["language"] = selected
        self.settings["language"] = selected
        save_settings(self.settings)
        # Détrompeur dans la langue choisie
        from bbs_popcorn.i18n import _STRINGS
        note = _STRINGS.get(selected, _STRINGS["fr"]).get("lang_restart", "")
        self.lang_restart_label.set_text(note)
        self.lang_restart_label.set_visible(True)
        # Fermer le popover — restart note déjà visible, settings auto-sauvegardés
        GLib.timeout_add(600, lambda: self._settings_popover.popdown() or False)

    def _sync_scale_sensitivity(self):
        enabled = self.pending_settings.get("window_mode", "windowed") != "fullscreen"
        self.scale_slider.set_sensitive(enabled)
        self.scale_label.set_sensitive(enabled)
        self.scale_spin.set_sensitive(enabled)
