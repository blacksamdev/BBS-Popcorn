import os
import json
import subprocess
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")

from gi.repository import Gtk, WebKit, GLib

from bbs_popcorn.player import MpvPlayer
from bbs_popcorn.updater import HostUpdater


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

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass

    return {"theme": "auto"}


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

        btn_settings = Gtk.MenuButton(label="⚙")

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

        cookie_manager.set_accept_policy(
            WebKit.CookieAcceptPolicy.ALWAYS
        )

        settings = self.webview.get_settings()
        settings.set_enable_javascript(True)
        settings.set_enable_media(True)
        settings.set_enable_html5_local_storage(True)

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
        self.url_bar.connect("activate", self.on_url_entered)

        self.webview.connect("load-changed", self.on_load_changed)

        vbox.append(navbar)
        vbox.append(self.webview)

        # ───────── Window ─────────
        self.win.set_child(vbox)
        self.win.present()

        # ───────── Player ─────────
        self.player = MpvPlayer(
            self.cookie_db_path,
            self.cookie_export_path,
            self.win
        )

        self.player.on_show_loading = lambda: None
        self.player.on_hide_loading = lambda: None

        # ───────── Updater ─────────
        updater = HostUpdater(on_done=self._on_update_done)
        updater.check_and_update()

    # ───────── Navigation ─────────

    def on_url_entered(self, entry):
        url = entry.get_text()

        if not url.startswith("http"):
            url = "https://" + url

        self.webview.load_uri(url)

    def on_load_changed(self, webview, event):
        if event == WebKit.LoadEvent.COMMITTED:
            self.url_bar.set_text(webview.get_uri())

        if event == WebKit.LoadEvent.FINISHED:
            self.inject_interceptor()

    # ───────── JS injection ─────────

    def inject_interceptor(self):
        js = """
        (function () {
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
        self.player.play(url)

    # ───────── Update callback ─────────

    def _on_update_done(self, msg: str):
        print(msg)
        return False
