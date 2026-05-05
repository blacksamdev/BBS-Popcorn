import os
import json
import threading
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")

from gi.repository import Gtk, WebKit, GLib

from bbs_popcorn.history_store import HistoryStore
from bbs_popcorn.logging_utils import log_event
from bbs_popcorn.player import MpvPlayer
from bbs_popcorn.updater import Updater


YOUTUBE_URL = "https://www.youtube.com"


def format_timestamp(seconds: float) -> str:
    """Formate un nombre de secondes en mm:ss."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"


SETTINGS_FILE = os.path.join(
    GLib.get_user_config_dir(),
    "bbs-popcorn",
    "settings.json"
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
    }

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                loaded = json.load(f)
                if not isinstance(loaded, dict):
                    return defaults
                settings = defaults.copy()
                settings.update(loaded)
                if settings.get("playback_profile") not in {"gaming", "quality"}:
                    settings["playback_profile"] = "gaming"
                if settings.get("quality_target") not in {"2160", "1440", "1080", "720", "480"}:
                    settings["quality_target"] = "1080"
                if settings.get("window_mode") not in {"fullscreen", "windowed"}:
                    settings["window_mode"] = "windowed"
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

    def __init__(self, cookie_db_path: str, cookie_export_path: str, sponsorblock_script_path: str = None):
        super().__init__(application_id="io.github.blacksamdev.Popcorn")
        self.connect("activate", self.on_activate)

        self.cookie_db_path = cookie_db_path
        self.cookie_export_path = cookie_export_path
        self.sponsorblock_script_path = sponsorblock_script_path
        self.settings = load_settings()
        self.history = HistoryStore()

    # ───────────── Activation ─────────────

    def on_activate(self, app):
        self._harden_cookie_paths()
        self.win = Gtk.ApplicationWindow(application=app)
        self.win.set_title("BBS Popcorn")
        self.win.set_default_size(1280, 800)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # ───────── Navigation ─────────
        navbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        btn_back = Gtk.Button(label="◀")
        btn_forward = Gtk.Button(label="▶")
        btn_reload = Gtk.Button(label="↺")
        btn_home = Gtk.Button(label="⌂")

        self.url_bar = Gtk.Entry()
        self.url_bar.set_hexpand(True)
        self.url_bar.set_text(YOUTUBE_URL)
        self.url_bar.set_editable(True)
        self.url_bar.set_can_focus(True)
        self.url_bar.connect("activate", self._on_url_bar_activate)

        self.btn_history = Gtk.MenuButton(label="🕐")
        self.btn_history.set_tooltip_text("Historique")

        btn_settings = Gtk.MenuButton(label="⚙")
        btn_settings.set_popover(self._build_settings_popover())

        navbar.append(btn_back)
        navbar.append(btn_forward)
        navbar.append(btn_reload)
        navbar.append(btn_home)
        navbar.append(self.url_bar)
        navbar.append(self.btn_history)
        navbar.append(btn_settings)

        # ───────── WebKit bridge ─────────
        self.content_manager = WebKit.UserContentManager()
        self.content_manager.register_script_message_handler("bbspopcorn")

        self.content_manager.connect(
            "script-message-received::bbspopcorn",
            self.on_js_message
        )

        # ───────── WebView ─────────
        self.webview = WebKit.WebView(
            user_content_manager=self.content_manager
        )

        network_session = self.webview.get_network_session()
        cookie_manager = network_session.get_cookie_manager()
        cookie_manager.set_persistent_storage(
            self.cookie_db_path,
            WebKit.CookiePersistentStorage.SQLITE
        )

        cookie_manager.set_accept_policy(WebKit.CookieAcceptPolicy.NO_THIRD_PARTY)

        settings = self.webview.get_settings()
        settings.set_enable_javascript(True)
        settings.set_enable_media(True)
        settings.set_enable_html5_local_storage(True)
        settings.set_media_playback_requires_user_gesture(False)

        settings.set_user_agent(
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120 Safari/537.36"
        )

        self.webview.set_vexpand(True)
        self.webview.load_uri(YOUTUBE_URL)

        btn_back.connect("clicked", lambda _: self.webview.go_back())
        btn_forward.connect("clicked", lambda _: self.webview.go_forward())
        btn_reload.connect("clicked", lambda _: self.webview.reload())
        btn_home.connect("clicked", lambda _: self.webview.load_uri(YOUTUBE_URL))

        self.webview.connect("load-changed", self.on_load_changed)
        self.webview.connect("decide-policy", self.on_decide_policy)

        vbox.append(navbar)
        self.content_overlay = Gtk.Overlay()
        self.content_overlay.set_child(self.webview)

        loading_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        loading_box.set_halign(Gtk.Align.CENTER)
        loading_box.set_valign(Gtk.Align.CENTER)
        loading_box.add_css_class("loading-overlay")

        self.loading_spinner = Gtk.Spinner()
        self.loading_spinner.set_size_request(64, 64)
        loading_box.append(self.loading_spinner)
        self.loading_label = Gtk.Label(label="Chargement de la video...")
        loading_box.append(self.loading_label)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            .loading-overlay {
                background-color: rgba(34, 38, 43, 0.92);
                border-radius: 12px;
                padding: 18px 22px;
            }
            .loading-overlay label {
                color: #d7dde5;
                font-size: 1.05em;
            }
            .status-bar {
                background-color: rgba(34, 38, 43, 0.85);
                padding: 4px 10px;
            }
            .status-bar label {
                color: #d7dde5;
            }
        """)
        Gtk.StyleContext.add_provider_for_display(
            self.win.get_display(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.loading_revealer = Gtk.Revealer()
        self.loading_revealer.set_transition_type(Gtk.RevealerTransitionType.CROSSFADE)
        self.loading_revealer.set_reveal_child(False)
        self.loading_revealer.set_can_target(False)
        self.loading_revealer.set_child(loading_box)

        self.content_overlay.add_overlay(self.loading_revealer)
        vbox.append(self.content_overlay)

        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        status_box.add_css_class("status-bar")
        self.status_label = Gtk.Label(label="Pret.")
        self.status_label.set_halign(Gtk.Align.START)
        status_box.append(self.status_label)
        vbox.append(status_box)

        # ───────── Window ─────────
        self.win.set_child(vbox)
        self.win.connect("destroy", self._on_shutdown)
        self.win.present()

        # ───────── Player ─────────
        self.player = MpvPlayer(
            self.cookie_db_path,
            self.cookie_export_path,
            self.win,
            playback_profile=self.settings.get("playback_profile", "gaming"),
            sponsorblock_script_path=self.sponsorblock_script_path,
        )

        self.player.on_show_loading = self._show_loading_overlay
        self.player.on_hide_loading = self._hide_loading_overlay
        self.player.on_show_notice = self._show_loading_notice
        self.player.on_status_change = self._set_status
        self._apply_player_settings()
        self.player.prefetch_cookies()
        self.player.prewarm_mpv()
        self.btn_history.set_popover(self._build_history_popover())
        threading.Thread(target=self._check_dependencies, daemon=True).start()

    def _check_dependencies(self):
        """Vérifie les dépendances en arrière-plan et avertit via la status bar."""
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

    # ───────── Navigation ─────────

    def on_load_changed(self, webview, event):
        if event == WebKit.LoadEvent.COMMITTED:
            self.url_bar.set_text(webview.get_uri())

        if event == WebKit.LoadEvent.FINISHED:
            self.inject_interceptor()

    def on_decide_policy(self, webview, decision, decision_type):
        if decision_type != WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            return False
        action = decision.get_navigation_action()
        if not action:
            return False
        request = action.get_request()
        if not request:
            return False
        uri = request.get_uri() or ""
        if self._is_allowed_uri(uri):
            return False
        decision.ignore()
        self._set_status("Navigation hors YouTube bloquee.")
        return True

    def _is_allowed_uri(self, uri: str) -> bool:
        allowed_prefixes = (
            "https://www.youtube.com",
            "https://youtube.com",
            "https://m.youtube.com",
            "https://youtu.be",
            "about:blank",
        )
        return uri.startswith(allowed_prefixes)

    # ───────── JS injection ─────────

    def inject_interceptor(self):
        js = """
        (function () {
            if (window.__bbspopcornInjected) return;
            window.__bbspopcornInjected = true;

            function disableSpeechApis() {
                try {
                    if (window.speechSynthesis) {
                        window.speechSynthesis.cancel();
                        window.speechSynthesis.speak = function () {};
                    }
                } catch (_) {}

                try {
                    window.SpeechRecognition = undefined;
                    window.webkitSpeechRecognition = undefined;
                } catch (_) {}
            }

            function forceShortsAudio() {
                if (!location.pathname.includes('/shorts/')) return;

                const enableAudio = () => {
                    const video = document.querySelector('video');
                    if (!video) return;
                    video.muted = false;
                    if (video.volume === 0) video.volume = 1;
                    if (video.paused) {
                        video.play().catch(() => {});
                    }
                };

                const muteSecondaryMedia = () => {
                    const mainVideo = document.querySelector('video');
                    const mediaNodes = document.querySelectorAll('audio, video');
                    for (const node of mediaNodes) {
                        if (node !== mainVideo) {
                            node.muted = true;
                            node.volume = 0;
                        }
                    }
                };

                enableAudio();
                muteSecondaryMedia();
                setTimeout(() => {
                    enableAudio();
                    muteSecondaryMedia();
                }, 300);

                const observer = new MutationObserver(() => {
                    enableAudio();
                    muteSecondaryMedia();
                });
                observer.observe(document.body, {childList: true, subtree: true});

                document.addEventListener("yt-navigate-finish", () => {
                    enableAudio();
                    muteSecondaryMedia();
                }, true);
            }

            function intercept(e) {
                const a = e.target.closest('a[href]');
                if (!a) return;

                const href = a.href;

                if (
                    href.includes("youtube.com/watch") ||
                    href.includes("youtube.com/playlist")
                ) {
                    e.preventDefault();
                    e.stopPropagation();
                    window.webkit.messageHandlers.bbspopcorn.postMessage(href);
                }
            }

            document.removeEventListener('click', intercept, true);
            document.addEventListener('click', intercept, true);
            disableSpeechApis();
            forceShortsAudio();
        })();
        """

        self.webview.evaluate_javascript(
            js,
            -1,
            None,
            None,
            None,
            None,
            None
        )

    # ───────── Messages JS ─────────

    def on_js_message(self, manager, message):
        url = message.to_string()
        print(f"[BBS Popcorn] Play: {url}")
        log_event(f"Play request: {url}")
        self.history.add(url, title=self.webview.get_title() or "")
        resume_pos = self.player._resume.get(url)
        if resume_pos:
            self._set_status(f"Reprise a {format_timestamp(resume_pos)}...")
        self.player.play(url)

    def _on_url_bar_activate(self, entry):
        url = entry.get_text().strip()
        if not url:
            return
        if not url.startswith("http"):
            url = "https://" + url
        if "youtube.com/watch" in url or "youtube.com/playlist" in url or "youtu.be/" in url:
            print(f"[BBS Popcorn] Play from URL bar: {url}")
            log_event(f"Play request (url bar): {url}")
            self.history.add(url, title=self.webview.get_title() or "")
            resume_pos = self.player._resume.get(url)
            if resume_pos:
                self._set_status(f"Reprise a {format_timestamp(resume_pos)}...")
            self.player.play(url)
        else:
            self.webview.load_uri(url)

    def _on_shutdown(self, _win):
        self.player.cleanup()

    # ───────── Loading overlay ─────────

    def _show_loading_overlay(self):
        self.loading_label.set_text("Chargement de la video...")
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
        self._history_popover = popover
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(10)
        box.set_margin_end(10)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title_label = Gtk.Label(label="Historique")
        title_label.set_hexpand(True)
        title_label.set_xalign(0)
        header.append(title_label)
        btn_clear = Gtk.Button(label="Effacer")
        btn_clear.connect("clicked", self._on_history_clear)
        header.append(btn_clear)
        box.append(header)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(200)
        scrolled.set_max_content_height(400)
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
            lbl = Gtk.Label(label="Aucun historique.")
            lbl.set_margin_top(8)
            lbl.set_margin_bottom(8)
            self._history_list_box.append(lbl)
            return

        for entry in entries:
            url = entry.get("url", "")
            title = entry.get("title", url)
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            row_box.set_margin_top(4)
            row_box.set_margin_bottom(4)
            lbl = Gtk.Label(label=title[:60] + ("…" if len(title) > 60 else ""))
            lbl.set_hexpand(True)
            lbl.set_xalign(0)
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
            self._set_status(f"Reprise a {format_timestamp(resume_pos)}...")
        self.player.play(url)

    def _on_history_clear(self, _btn):
        self.history.clear()
        self._refresh_history_list()

    # ───────── Settings popover ─────────

    def _build_settings_popover(self):
        self.pending_settings = dict(self.settings)
        popover = Gtk.Popover()
        self._settings_popover = popover
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(10)
        box.set_margin_end(10)

        quality_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        quality_label = Gtk.Label(label="Qualite max:")
        quality_label.set_xalign(0)
        quality_row.append(quality_label)
        self.quality_combo = Gtk.ComboBoxText()
        for q in ["2160", "1440", "1080", "720", "480"]:
            self.quality_combo.append_text(q)
        self.quality_combo.set_active(["2160", "1440", "1080", "720", "480"].index(self.pending_settings["quality_target"]))
        self.quality_combo.connect("changed", self._on_settings_changed)
        quality_row.append(self.quality_combo)
        box.append(quality_row)

        mode_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        mode_label = Gtk.Label(label="Mode fenetre:")
        mode_label.set_xalign(0)
        mode_row.append(mode_label)
        self.mode_combo = Gtk.ComboBoxText()
        self.mode_combo.append("windowed", "Fenetre")
        self.mode_combo.append("fullscreen", "Plein ecran")
        self.mode_combo.set_active_id(self.pending_settings["window_mode"])
        self.mode_combo.connect("changed", self._on_settings_changed)
        mode_row.append(self.mode_combo)
        box.append(mode_row)

        scale_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.scale_label = Gtk.Label(label=f"Taille: {self.pending_settings['window_scale_percent']}%")
        self.scale_label.set_xalign(0)
        scale_row.append(self.scale_label)
        self.scale_adjustment = Gtk.Adjustment(
            value=float(self.pending_settings["window_scale_percent"]),
            lower=50.0,
            upper=100.0,
            step_increment=5.0,
            page_increment=10.0,
            page_size=0.0
        )
        self.scale_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.scale_adjustment)
        self.scale_slider.set_draw_value(False)
        self.scale_slider.connect("value-changed", self._on_scale_changed)
        scale_row.append(self.scale_slider)
        self.scale_spin = Gtk.SpinButton(adjustment=self.scale_adjustment, climb_rate=1.0, digits=0)
        self.scale_spin.set_numeric(True)
        self.scale_spin.connect("value-changed", self._on_scale_changed)
        scale_row.append(self.scale_spin)
        box.append(scale_row)

        sponsorblock_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        sponsorblock_label = Gtk.Label(label="SponsorBlock:")
        sponsorblock_label.set_xalign(0)
        sponsorblock_label.set_hexpand(True)
        sponsorblock_row.append(sponsorblock_label)
        self.sponsorblock_switch = Gtk.Switch()
        self.sponsorblock_switch.set_active(self.pending_settings.get("sponsorblock_enabled", False))
        self.sponsorblock_switch.connect("state-set", self._on_sponsorblock_changed)
        if not self.sponsorblock_script_path:
            self.sponsorblock_switch.set_sensitive(False)
            sponsorblock_label.set_tooltip_text("Script SponsorBlock non disponible dans ce build.")
        sponsorblock_row.append(self.sponsorblock_switch)
        box.append(sponsorblock_row)

        help_label = Gtk.Label(
            label=(
                "Lecture externe : la video s'ouvre dans MPV.\n"
                "Pour revenir a YouTube, fermez la fenetre MPV."
            )
        )
        help_label.set_xalign(0)
        help_label.set_wrap(True)
        help_label.set_max_width_chars(36)
        box.append(help_label)

        self.save_button = Gtk.Button(label="Save")
        self.save_button.set_sensitive(False)
        self.save_button.connect("clicked", self._on_save_clicked)
        box.append(self.save_button)

        popover.set_child(box)
        self._sync_scale_sensitivity()
        self._sync_save_button_state()
        return popover

    def _on_sponsorblock_changed(self, switch, state):
        self.pending_settings["sponsorblock_enabled"] = state
        self._sync_save_button_state()

    def _on_scale_changed(self, scale):
        value = int(scale.get_value())
        self.scale_label.set_text(f"Taille: {value}%")
        self.pending_settings["window_scale_percent"] = value
        self._sync_save_button_state()

    def _on_settings_changed(self, *_args):
        self.pending_settings["quality_target"] = self.quality_combo.get_active_text() or "1080"
        self.pending_settings["window_mode"] = self.mode_combo.get_active_id() or "windowed"
        self._sync_scale_sensitivity()
        self._sync_save_button_state()

    def _on_save_clicked(self, _button):
        self.settings.update(self.pending_settings)
        save_settings(self.settings)
        self._apply_player_settings()
        self._sync_save_button_state()
        if hasattr(self, "_settings_popover"):
            self._settings_popover.popdown()

    def _apply_player_settings(self):
        self.player.update_playback_settings(
            quality_target=self.settings.get("quality_target", "1080"),
            window_mode=self.settings.get("window_mode", "windowed"),
            window_scale_percent=int(self.settings.get("window_scale_percent", 80)),
            sponsorblock_enabled=bool(self.settings.get("sponsorblock_enabled", False)),
        )

    def _sync_scale_sensitivity(self):
        window_mode = self.pending_settings.get("window_mode", "windowed")
        enabled = window_mode != "fullscreen"
        self.scale_slider.set_sensitive(enabled)
        self.scale_label.set_sensitive(enabled)
        self.scale_spin.set_sensitive(enabled)

    def _sync_save_button_state(self):
        has_changes = any(
            self.settings.get(key) != self.pending_settings.get(key)
            for key in ("quality_target", "window_mode", "window_scale_percent", "sponsorblock_enabled")
        )
        self.save_button.set_sensitive(has_changes)
