import os
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')
from gi.repository import Gtk, WebKit, GLib

from player import MpvPlayer
from updater import HostUpdater

YOUTUBE_URL = "https://www.youtube.fr"


class YtMpvApp(Gtk.Application):
    def __init__(self, cookie_db_path: str, cookie_export_path: str):
        super().__init__(application_id="io.github.blacksamdev.Popcorn")
        self.connect("activate", self.on_activate)

        self.cookie_db_path     = cookie_db_path
        self.cookie_export_path = cookie_export_path

    # ── Activation ──────────────────────────────

    def on_activate(self, app):
        self.win = Gtk.ApplicationWindow(application=app)
        self.win.set_title("BBS Popcorn")
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

        for w in (btn_back, btn_forward, btn_reload, btn_home, self.url_bar):
            navbar.append(w)

        # ── Content manager JS → Python ──────────
        self.content_manager = WebKit.UserContentManager()
        self.content_manager.register_script_message_handler("bbspopcorn")
        self.content_manager.connect(
            "script-message-received::bbspopcorn",
            self.on_js_message
        )

        # ── WebView ──────────────────────────────
        self.webview = WebKit.WebView(user_content_manager=self.content_manager)

        # Cookies persistants
        network_session = self.webview.get_network_session()
        cookie_manager  = network_session.get_cookie_manager()
        cookie_manager.set_persistent_storage(
            self.cookie_db_path,
            WebKit.CookiePersistentStorage.SQLITE
        )
        cookie_manager.set_accept_policy(WebKit.CookieAcceptPolicy.ALWAYS)

        # Paramètres WebKit
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

        # Boutons navigation
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
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string("""
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
            .update-bar label {
                color: white;
                font-size: 13px;
            }
            .update-bar button {
                background: none;
                border: none;
                color: white;
                font-size: 13px;
            }
        """)
        Gtk.StyleContext.add_provider_for_display(
            self.win.get_display(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

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

        # ── Mises à jour hôte en arrière-plan ────
        updater = HostUpdater(on_done=self._on_update_done)
        updater.check_and_update()

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
