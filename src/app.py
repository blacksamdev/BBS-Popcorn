import os
import subprocess
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')
from gi.repository import Gtk, WebKit, GLib, Gio

from player import MpvPlayer
from updater import HostUpdater

YOUTUBE_URL = "https://www.youtube.fr"
SETTINGS_FILE = os.path.join(GLib.get_user_config_dir(), "bbs-popcorn", "settings.json")


def load_settings() -> dict:
    import json
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"theme": "auto"}


def save_settings(settings: dict):
    import json
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)


def detect_system_theme() -> str:
    """Détecte le thème système KDE/GTK — retourne 'dark' ou 'light'."""
    try:
        # KDE
        result = subprocess.run(
            ["kreadconfig5", "--group", "General", "--key", "ColorScheme"],
            capture_output=True, text=True
        )
        if "dark" in result.stdout.lower():
            return "dark"
        # GTK via gsettings
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
            capture_output=True, text=True
        )
        if "dark" in result.stdout.lower():
            return "dark"
    except Exception:
        pass
    return "light"


class YtMpvApp(Gtk.Application):
    def __init__(self, cookie_db_path: str, cookie_export_path: str):
        super().__init__(application_id="io.github.blacksamdev.Popcorn")
        self.connect("activate", self.on_activate)

        self.cookie_db_path     = cookie_db_path
        self.cookie_export_path = cookie_export_path
        self.settings           = load_settings()

    # ── Activation ──────────────────────────────

    def on_activate(self, app):
        self.win = Gtk.ApplicationWindow(application=app)
        self.win.set_title("BBS pOpcOrn")
        self.win.set_default_size(1280, 800)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # ── Barre de navigation ──────────────────
        navbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        navbar.set_margin_start(8)
        navbar.set_margin_end(8)
        navbar.set_margin_top(4)
        navbar.set_margin_bottom(4)

        btn_back    = Gtk.Button(label="◀")
        btn_forward = Gtk.Button(label="▶")
        btn_reload  = Gtk.Button(label="↺")
        btn_home    = Gtk.Button(label="⌂")

        self.url_bar = Gtk.Entry()
        self.url_bar.set_hexpand(True)
        self.url_bar.set_text(YOUTUBE_URL)

        btn_settings = Gtk.MenuButton()
        btn_settings.set_label("⚙")
        btn_settings.set_tooltip_text("Paramètres")

        for w in (btn_back, btn_forward, btn_reload, btn_home, self.url_bar, btn_settings):
            navbar.append(w)

        # ── Popover paramètres ───────────────────
        popover = Gtk.Popover()
        popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        popover_box.set_margin_start(16)
        popover_box.set_margin_end(16)
        popover_box.set_margin_top(12)
        popover_box.set_margin_bottom(12)

        # Titre
        title_label = Gtk.Label()
        title_label.set_markup("<b>BBS pOpcOrn — Paramètres</b>")
        title_label.set_xalign(0)
        popover_box.append(title_label)

        # Séparateur
        popover_box.append(Gtk.Separator())

        # Thème
        theme_label = Gtk.Label(label="Thème")
        theme_label.set_xalign(0)
        popover_box.append(theme_label)

        theme_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.btn_theme_auto  = Gtk.ToggleButton(label="Auto")
        self.btn_theme_light = Gtk.ToggleButton(label="☀ Clair")
        self.btn_theme_dark  = Gtk.ToggleButton(label="☾ Sombre")

        # Groupe radio
        self.btn_theme_light.set_group(self.btn_theme_auto)
        self.btn_theme_dark.set_group(self.btn_theme_auto)

        current = self.settings.get("theme", "auto")
        if current == "light":
            self.btn_theme_light.set_active(True)
        elif current == "dark":
            self.btn_theme_dark.set_active(True)
        else:
            self.btn_theme_auto.set_active(True)

        self.btn_theme_auto.connect ("toggled", self._on_theme_changed, "auto")
        self.btn_theme_light.connect("toggled", self._on_theme_changed, "light")
        self.btn_theme_dark.connect ("toggled", self._on_theme_changed, "dark")

        theme_box.append(self.btn_theme_auto)
        theme_box.append(self.btn_theme_light)
        theme_box.append(self.btn_theme_dark)
        popover_box.append(theme_box)

        popover.set_child(popover_box)
        btn_settings.set_popover(popover)

        # ── Content manager JS → Python ──────────
        self.content_manager = WebKit.UserContentManager()
        self.content_manager.register_script_message_handler("bbspopcorn")
        self.content_manager.connect(
            "script-message-received::bbspopcorn",
            self.on_js_message
        )

        # ── WebView ──────────────────────────────
        self.webview = WebKit.WebView(user_content_manager=self.content_manager)

        network_session = self.webview.get_network_session()
        cookie_manager  = network_session.get_cookie_manager()
        cookie_manager.set_persistent_storage(
            self.cookie_db_path,
            WebKit.CookiePersistentStorage.SQLITE
        )
        cookie_manager.set_accept_policy(WebKit.CookieAcceptPolicy.ALWAYS)

        settings = self.webview.get_settings()
        settings.set_enable_javascript(True)
        settings.set_enable_media(True)
        settings.set_enable_html5_local_storage(True)
        settings.set_hardware_acceleration_policy(
            WebKit.HardwareAccelerationPolicy.ALWAYS
        )
        settings.set_user_agent(
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        self.webview.set_vexpand(True)
        self.webview.load_uri(YOUTUBE_URL)

        btn_back.connect    ("clicked", lambda _: self.webview.go_back())
        btn_forward.connect ("clicked", lambda _: self.webview.go_forward())
        btn_reload.connect  ("clicked", lambda _: self.webview.reload())
        btn_home.connect    ("clicked", lambda _: self.webview.load_uri(YOUTUBE_URL))
        self.url_bar.connect("activate", self.on_url_entered)
        self.webview.connect("load-changed", self.on_load_changed)

        vbox.append(navbar)
        vbox.append(self.webview)

        # ── Overlay chargement ───────────────────
        self.overlay = Gtk.Overlay()
        self.overlay.set_child(vbox)

        self.loading_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16
        )
        self.loading_box.set_halign(Gtk.Align.CENTER)
        self.loading_box.set_valign(Gtk.Align.CENTER)
        self.loading_box.set_visible(False)
        self.loading_box.add_css_class("loading-overlay")

        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(64, 64)

        self.loading_label = Gtk.Label(label="🍿 Chargement MPV...")
        self.loading_label.add_css_class("loading-label")

        self.loading_box.append(self.spinner)
        self.loading_box.append(self.loading_label)
        self.overlay.add_overlay(self.loading_box)

        # ── Bandeau mise à jour ──────────────────
        self.update_bar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8
        )
        self.update_bar.set_halign(Gtk.Align.FILL)
        self.update_bar.set_valign(Gtk.Align.START)
        self.update_bar.set_margin_start(8)
        self.update_bar.set_margin_end(8)
        self.update_bar.set_margin_top(8)
        self.update_bar.set_visible(False)
        self.update_bar.add_css_class("update-bar")

        self.update_label = Gtk.Label(label="")
        self.update_label.set_hexpand(True)
        self.update_label.set_xalign(0)

        btn_close_bar = Gtk.Button(label="✕")
        btn_close_bar.connect("clicked", lambda _: self.update_bar.set_visible(False))

        self.update_bar.append(self.update_label)
        self.update_bar.append(btn_close_bar)
        self.overlay.add_overlay(self.update_bar)

        # ── CSS ──────────────────────────────────
        self.css_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            self.win.get_display(),
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self._apply_theme(self.settings.get("theme", "auto"))

        self.win.set_child(self.overlay)
        self.win.present()

        # ── Lecteur MPV ──────────────────────────
        self.player = MpvPlayer(
            self.cookie_db_path,
            self.cookie_export_path,
            self.win
        )
        self.player.on_show_loading = self._show_loading
        self.player.on_hide_loading = self._hide_loading

        # ── Mises à jour hôte ────────────────────
        updater = HostUpdater(on_done=self._on_update_done)
        updater.check_and_update()

    # ── Thème ────────────────────────────────────

    def _on_theme_changed(self, btn, theme_name: str):
        if btn.get_active():
            self.settings["theme"] = theme_name
            save_settings(self.settings)
            self._apply_theme(theme_name)

    def _apply_theme(self, theme: str):
        if theme == "auto":
            theme = detect_system_theme()

        if theme == "dark":
            css = """
                .loading-overlay {
                    background-color: rgba(20, 20, 20, 0.85);
                    border-radius: 16px;
                    padding: 32px 48px;
                }
                .loading-label {
                    color: #eeeeee;
                    font-size: 18px;
                    font-weight: bold;
                }
                .update-bar {
                    background-color: rgba(30, 100, 30, 0.90);
                    border-radius: 8px;
                    padding: 8px 12px;
                }
                .update-bar label { color: white; font-size: 13px; }
                .update-bar button {
                    background: none; border: none;
                    color: white; font-size: 13px;
                }
                window, .view {
                    background-color: #1e1e1e;
                    color: #eeeeee;
                }
                entry {
                    background-color: #2d2d2d;
                    color: #eeeeee;
                }
            """
        else:
            css = """
                .loading-overlay {
                    background-color: rgba(0, 0, 0, 0.75);
                    border-radius: 16px;
                    padding: 32px 48px;
                }
                .loading-label {
                    color: white;
                    font-size: 18px;
                    font-weight: bold;
                }
                .update-bar {
                    background-color: rgba(30, 120, 30, 0.90);
                    border-radius: 8px;
                    padding: 8px 12px;
                }
                .update-bar label { color: white; font-size: 13px; }
                .update-bar button {
                    background: none; border: none;
                    color: white; font-size: 13px;
                }
                window, .view {
                    background-color: #f5f5f5;
                    color: #1a1a1a;
                }
                entry {
                    background-color: #ffffff;
                    color: #1a1a1a;
                }
            """

        self.css_provider.load_from_string(css)

        # Notifie WebKit du thème
        if hasattr(self, 'webview'):
            color_scheme = (
                WebKit.ColorScheme.DARK
                if theme == "dark"
                else WebKit.ColorScheme.LIGHT
            )
            self.webview.get_settings().set_property(
                "hardware-acceleration-policy",
                WebKit.HardwareAccelerationPolicy.ALWAYS
            )

    # ── Navigation ───────────────────────────────

    def on_url_entered(self, entry):
        url = entry.get_text()
        if not url.startswith("http"):
            url = "https://" + url
        self.webview.load_uri(url)

    def on_load_changed(self, webview, event):
        if event == WebKit.LoadEvent.COMMITTED:
            uri = webview.get_uri()
            if uri:
                self.url_bar.set_text(uri)
        if event == WebKit.LoadEvent.FINISHED:
            self.inject_interceptor()

    # ── JS ───────────────────────────────────────

    def inject_interceptor(self):
        js = """
        (function() {
            function interceptClicks(e) {
                let el = e.target.closest('a[href]');
                if (!el) return;
                let href = el.href;
                if (href.match(/youtube\\.com\\/watch\\?/) ||
                    href.match(/youtube\\.com\\/playlist\\?/)) {
                    e.preventDefault();
                    e.stopPropagation();
                    window.webkit.messageHandlers.bbspopcorn.postMessage(href);
                }
            }
            document.removeEventListener('click', interceptClicks, true);
            document.addEventListener('click', interceptClicks, true);
        })();
        """
        self.webview.evaluate_javascript(js, -1, None, None, None, None, None)

    def on_js_message(self, content_manager, value):
        url = value.to_string()
        print(f"[popcorn] Interception JS : {url}")
        self.player.play(url)

    # ── Overlay chargement ───────────────────────

    def _show_loading(self):
        self.loading_box.set_visible(True)
        self.spinner.start()

    def _hide_loading(self):
        self.loading_box.set_visible(False)
        self.spinner.stop()

    # ── Callback mise à jour ─────────────────────

    def _on_update_done(self, msg: str):
        print(f"[updater] Terminé :\n{msg}")
        if "✓" in msg:
            self.update_label.set_text(msg.replace("\n", "  |  "))
            self.update_bar.set_visible(True)
            GLib.timeout_add_seconds(8, self._hide_update_bar)
        return False

    def _hide_update_bar(self):
        self.update_bar.set_visible(False)
        return False
