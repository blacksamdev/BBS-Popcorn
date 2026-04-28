import os
import sys
from gi.repository import GLib

from bbs_popcorn.app import YtMpvApp
from bbs_popcorn.updater import Updater


def check_dependencies():
    status = Updater.status()
    missing = []

    if not status.get("mpv", False):
        missing.append("MPV Flatpak manquant : flatpak install flathub io.mpv.Mpv")
    if not status.get("yt-dlp", False):
        missing.append("yt-dlp manquant dans l'application")

    if missing:
        print("\n=== Dépendances manquantes ===\n")
        for dep in missing:
            print(" -", dep)
        print("\nInstalle les dépendances puis relance l'application.\n")
        sys.exit(1)


def main():
    GLib.set_prgname("bbs-popcorn")
    GLib.set_application_name("BBS Popcorn")
    print("Popcorn starting...")
    check_dependencies()

    state_dir = os.path.join(GLib.get_user_data_dir(), "bbs-popcorn")
    os.makedirs(state_dir, mode=0o700, exist_ok=True)
    try:
        os.chmod(state_dir, 0o700)
    except OSError:
        pass

    cookie_db_path = os.path.join(state_dir, "cookies.sqlite")
    cookie_export_path = os.path.join(state_dir, "cookies.txt")

    app = YtMpvApp(cookie_db_path, cookie_export_path)
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
