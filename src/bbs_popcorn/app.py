import os
import threading
import json
import subprocess
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")

from gi.repository import Gtk, WebKit, GLib

from bbs_popcorn.logging_utils import log_event
from bbs_popcorn.history_store import HistoryStore
from bbs_popcorn.player import MpvPlayer


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
        "webkit_mode": "gourmand",
    }

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    settings = defaults.copy()
                    settings.update(loaded)
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
        self.url_bar.connect("activate", self._on_url_bar_activate)

        btn_settings = Gtk.MenuButton(label="⚙")
        btn_settings.set_popover(self._build_settings_popover())

        for b in[btn_back, btn_forward, btn_reload, btn_home]:
            navbar.append(b)
        navbar.append(self.url_bar)
        navbar.append(btn_settings)

        # ───────── WebKit ─────────
        self.content_manager = WebKit.UserContentManager()
        self.content_manager.register_script_message_handler("bbspopcorn")
        self.content_manager.connect("script-message-received::bbspopcorn", self.on_js_message)

        self.webview = WebKit.WebView(user_content_manager=self.content_manager)

        # Configuration WebKit (Paramètres fixes pour la stabilité)
        ws = self.webview.get_settings()
        ws.set_enable_javascript(True)
        ws.set_enable_media(True)
        ws.set_enable_html5_local_storage(True)
        ws.set_media_playback_requires_user_gesture(False)
        ws.set_enable_media_stream(False)
        ws.set_enable_encrypted_media(False)
        ws.set_user_agent("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")

        self._apply_webkit_mode(save=False)

        # Cookies
        network_session = self.webview.get_network_session()
        cookie_manager = network_session.get_cookie_manager()
        cookie_manager.set_persistent_storage(self.cookie_db_path, WebKit.CookiePersistentStorage.SQLITE)
        cookie_manager.set_accept_policy(WebKit.CookieAcceptPolicy.NO_THIRD_PARTY)

        self.webview.load_uri(YOUTUBE_URL)
        btn_back.connect("clicked", lambda _: self.webview.go_back())
        btn_forward.connect("clicked", lambda _: self.webview.go_forward())
        btn_reload.connect("clicked", lambda _: self.webview.reload())
        btn_home.connect("clicked", lambda _: self.webview.load_uri(YOUTUBE_URL))

        self.webview.connect("load-changed", self.on_load_changed)
        self.webview.connect("decide-policy", self.on_decide_policy)

        # ───────── UI Overlay ─────────
        vbox.append(navbar)
        self.content_overlay = Gtk.Overlay()
        self.content_overlay.set_child(self.webview)

        loading_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        loading_box.set_halign(Gtk.Align.CENTER)
        loading_box.set_valign(Gtk.Align.CENTER)
        self.loading_spinner = Gtk.Spinner()
        self.loading_spinner.set_size_request(64, 64)
        loading_box.append(self.loading_spinner)
        self.loading_label = Gtk.Label(label="Chargement...")
        loading_box.append(self.loading_label)

        self.loading_revealer = Gtk.Revealer()
        self.loading_revealer.set_child(loading_box)
        self.content_overlay.add_overlay(self.loading_revealer)
        vbox.append(self.content_overlay)

        self.status_label = Gtk.Label(label="Pret.")
        self.status_label.set_halign(Gtk.Align.START)
        vbox.append(self.status_label)

        self.win.set_child(vbox)
        self.win.connect("destroy", self._on_shutdown)
        self.win.present()

        # ───────── Player ─────────
        self.player = MpvPlayer(self.cookie_db_path, self.cookie_export_path, self.win,
                                playback_profile=self.settings.get("playback_profile", "gaming"),
                                sponsorblock_script_path=self.sponsorblock_script_path)
        self.player.on_show_loading = self._show_loading_overlay
        self.player.on_hide_loading = self._hide_loading_overlay
        self.player.on_status_change = self._set_status
        self.player._on_media_title = self._update_history_title
        self._apply_player_settings()

    def _apply_webkit_mode(self, save: bool = True):
        mode = self.settings.get("webkit_mode", "gourmand")
        ws = self.webview.get_settings()
        eco = (mode == "eco")
        ws.set_enable_webgl(not eco)
        ws.set_enable_webaudio(not eco)
        ws.set_hardware_acceleration_policy(WebKit.HardwareAccelerationPolicy.ON_DEMAND if eco else WebKit.HardwareAccelerationPolicy.ALWAYS)
        self.inject_interceptor()
        if save: save_settings(self.settings)

    def _harden_cookie_paths(self):
        state_dir = os.path.dirname(self.cookie_db_path)
        os.makedirs(state_dir, mode=0o700, exist_ok=True)

    # ───────── JS injection ─────────

    def inject_interceptor(self):
        eco_mode = "true" if self.settings.get("webkit_mode") == "eco" else "false"
        js = f"""
        (function () {{
            const ECO_MODE = {eco_mode};
            function intercept(e) {{
                const a = e.target.closest('a[href]');
                if (!a) return;
                const href = a.href;

                // En mode ECO, rediriger les Shorts vers MPV. Sinon, laisser WebKit gérer.
                if (href.includes("youtube.com/shorts/")) {{
                    if (ECO_MODE) {{
                        e.preventDefault(); e.stopPropagation();
                        const m = href.match(/[/]shorts[/]([a-zA-Z0-9_-]+)/);
                        if (m) window.webkit.messageHandlers.bbspopcorn.postMessage('https://www.youtube.com/watch?v=' + m[1]);
                    }}
                    return;
                }}
                if (href.includes("youtube.com/watch") || href.includes("youtube.com/playlist")) {{
                    e.preventDefault(); e.stopPropagation();
                    window.webkit.messageHandlers.bbspopcorn.postMessage(href);
                }}
            }}
            document.removeEventListener('click', intercept, true);
            document.addEventListener('click', intercept, true);
        }})();
        """
        self.webview.evaluate_javascript(js, -1, None, None, None, None, None)

    def on_js_message(self, manager, message):
        url = message.to_string()
        self.history.add(url, title=self.webview.get_title() or "Video")
        self.player.play(url)

    def on_load_changed(self, webview, event):
        if event == WebKit.LoadEvent.COMMITTED: self.url_bar.set_text(webview.get_uri())
        if event == WebKit.LoadEvent.FINISHED: self.inject_interceptor()

    def on_decide_policy(self, webview, decision, decision_type):
        if decision_type != WebKit.PolicyDecisionType.NAVIGATION_ACTION: return False
        uri = decision.get_request().get_uri() or ""
        if any(uri.startswith(p) for p in["https://www.youtube.com", "https://youtube.com", "https://m.youtube.com", "https://youtu.be", "about:blank"]):
            return False
        decision.ignore()
        return True

    def _on_url_bar_activate(self, entry):
        url = entry.get_text().strip()
        if "youtube.com/watch" in url or "youtube.com/playlist" in url or "youtu.be/" in url:
            self.history.add(url, title="URL Externe")
            self.player.play(url)
        else:
            self.webview.load_uri(url if url.startswith("http") else "https://" + url)

    def _update_history_title(self, url: str, title: str):
        self.history.add(url, title=title)
        return False

    def _on_shutdown(self, _win):
        self.player.cleanup()

    def _show_loading_overlay(self):
        self.loading_spinner.start()
        self.loading_revealer.set_reveal_child(True)

    def _hide_loading_overlay(self):
        self.loading_revealer.set_reveal_child(False)
        self.loading_spinner.stop()

    def _set_status(self, message: str):
        self.status_label.set_text(message)
        return False

    # ───────── Settings UI ─────────

    def _build_settings_popover(self):
        self.pending_settings = dict(self.settings)
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        self.quality_combo = Gtk.ComboBoxText()
        for q in["2160", "1440", "1080", "720", "480"]: self.quality_combo.append_text(q)
        self.quality_combo.set_active(["2160", "1440", "1080", "720", "480"].index(self.pending_settings.get("quality_target", "1080")))
        box.append(self.quality_combo)

        self.webkit_mode_combo = Gtk.ComboBoxText()
        self.webkit_mode_combo.append("gourmand", "🎬 Gourmand")
        self.webkit_mode_combo.append("eco", "🌿 Éco")
        self.webkit_mode_combo.set_active_id(self.pending_settings.get("webkit_mode", "gourmand"))
        box.append(self.webkit_mode_combo)

        self.save_button = Gtk.Button(label="Save")
        self.save_button.connect("clicked", self._on_save_clicked)
        box.append(self.save_button)

        popover.set_child(box)
        return popover

    def _on_save_clicked(self, _button):
        self.settings["quality_target"] = self.quality_combo.get_active_text()
        self.settings["webkit_mode"] = self.webkit_mode_combo.get_active_id()
        save_settings(self.settings)
        self._apply_player_settings()
        self._apply_webkit_mode(save=False)

    def _apply_player_settings(self):
        self.player.update_playback_settings(
            quality_target=self.settings.get("quality_target", "1080"),
            window_mode=self.settings.get("window_mode", "windowed"),
            window_scale_percent=int(self.settings.get("window_scale_percent", 80)),
            sponsorblock_enabled=bool(self.settings.get("sponsorblock_enabled", False)),
        )
