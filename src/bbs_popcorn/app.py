import os
import json
import subprocess
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")

from gi.repository import Gtk, WebKit, GLib

from bbs_popcorn.logging_utils import log_event
from bbs_popcorn.player import MpvPlayer


YOUTUBE_URL = "https://www.youtube.com"

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
        "quality_bias": "high",
        "window_mode": "windowed",
        "window_scale_percent": 80,
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
                if settings.get("quality_bias") not in {"high", "low"}:
                    settings["quality_bias"] = "high"
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


def detect_system_theme() -> str:
    try:
        result = subprocess.run(
            [
                "gsettings",
                "get",
                "org.gnome.desktop.interface",
                "color-scheme"
            ],
            capture_output=True,
            text=True
        )
        if "dark" in result.stdout.lower():
            return "dark"
    except Exception:
        pass

    return "light"


# ─────────────────────────────
# App
# ─────────────────────────────

class YtMpvApp(Gtk.Application):

    def __init__(self, cookie_db_path: str, cookie_export_path: str):
        super().__init__(application_id="io.github.blacksamdev.Popcorn")
        self.connect("activate", self.on_activate)

        self.cookie_db_path = cookie_db_path
        self.cookie_export_path = cookie_export_path
        self.settings = load_settings()

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
        self.url_bar.set_editable(False)
        self.url_bar.set_can_focus(False)

        btn_settings = Gtk.MenuButton(label="⚙")
        btn_settings.set_popover(self._build_settings_popover())

        navbar.append(btn_back)
        navbar.append(btn_forward)
        navbar.append(btn_reload)
        navbar.append(btn_home)
        navbar.append(self.url_bar)
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
        self.win.present()

        # ───────── Player ─────────
        self.player = MpvPlayer(
            self.cookie_db_path,
            self.cookie_export_path,
            self.win,
            playback_profile=self.settings.get("playback_profile", "gaming")
        )

        self.player.on_show_loading = self._show_loading_overlay
        self.player.on_hide_loading = self._hide_loading_overlay
        self.player.on_show_notice = self._show_loading_notice
        self.player.on_status_change = self._set_status
        self._apply_player_settings()

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
        request = decision.get_request()
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

    def on_js_message(self, manager, message):
        url = message.to_string()
        print(f"[BBS Popcorn] Play: {url}")
        log_event(f"Play request: {url}")
        self.player.play(url)

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

    def _build_settings_popover(self):
        popover = Gtk.Popover()
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
        self.quality_combo.set_active(["2160", "1440", "1080", "720", "480"].index(self.settings["quality_target"]))
        self.quality_combo.connect("changed", self._on_settings_changed)
        quality_row.append(self.quality_combo)
        box.append(quality_row)

        bias_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bias_label = Gtk.Label(label="Priorite:")
        bias_label.set_xalign(0)
        bias_row.append(bias_label)
        self.bias_combo = Gtk.ComboBoxText()
        self.bias_combo.append("high", "Plus haute")
        self.bias_combo.append("low", "Plus basse")
        self.bias_combo.set_active_id(self.settings["quality_bias"])
        self.bias_combo.connect("changed", self._on_settings_changed)
        bias_row.append(self.bias_combo)
        box.append(bias_row)

        mode_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        mode_label = Gtk.Label(label="Mode fenetre:")
        mode_label.set_xalign(0)
        mode_row.append(mode_label)
        self.mode_combo = Gtk.ComboBoxText()
        self.mode_combo.append("windowed", "Fenetre")
        self.mode_combo.append("fullscreen", "Plein ecran")
        self.mode_combo.set_active_id(self.settings["window_mode"])
        self.mode_combo.connect("changed", self._on_settings_changed)
        mode_row.append(self.mode_combo)
        box.append(mode_row)

        scale_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.scale_label = Gtk.Label(label=f"Taille: {self.settings['window_scale_percent']}%")
        self.scale_label.set_xalign(0)
        scale_row.append(self.scale_label)
        self.scale_adjustment = Gtk.Adjustment(
            value=float(self.settings["window_scale_percent"]),
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
        box.append(scale_row)

        popover.set_child(box)
        return popover

    def _on_scale_changed(self, scale):
        value = int(scale.get_value())
        self.scale_label.set_text(f"Taille: {value}%")
        self.settings["window_scale_percent"] = value
        self._save_and_apply_settings()

    def _on_settings_changed(self, *_args):
        self.settings["quality_target"] = self.quality_combo.get_active_text() or "1080"
        self.settings["quality_bias"] = self.bias_combo.get_active_id() or "high"
        self.settings["window_mode"] = self.mode_combo.get_active_id() or "windowed"
        self._save_and_apply_settings()

    def _save_and_apply_settings(self):
        save_settings(self.settings)
        self._apply_player_settings()

    def _apply_player_settings(self):
        self.player.update_playback_settings(
            quality_target=self.settings.get("quality_target", "1080"),
            quality_bias=self.settings.get("quality_bias", "high"),
            window_mode=self.settings.get("window_mode", "windowed"),
            window_scale_percent=int(self.settings.get("window_scale_percent", 80)),
        )
