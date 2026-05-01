import os
import sys
import shutil
from gi.repository import GLib

from bbs_popcorn.app import YtMpvApp
from bbs_popcorn.updater import Updater

# Bundled script location inside the Flatpak.
_BUNDLED_SPONSORBLOCK = "/app/share/bbs-popcorn/sponsorblock.lua"


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
    GLib.set_application_name("BBS pOpcOrn")
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

    # Copy the bundled SponsorBlock script to state_dir so MPV Flatpak
    # can access it via --filesystem= (same mechanism as cookies).
    sponsorblock_script_path = None
    dest = os.path.join(state_dir, "sponsorblock.lua")
    if os.path.exists(_BUNDLED_SPONSORBLOCK):
        try:
            if not os.path.exists(dest) or (
                os.path.getmtime(_BUNDLED_SPONSORBLOCK) > os.path.getmtime(dest)
            ):
                shutil.copy2(_BUNDLED_SPONSORBLOCK, dest)
                os.chmod(dest, 0o600)
            sponsorblock_script_path = dest
        except OSError:
            pass

    app = YtMpvApp(cookie_db_path, cookie_export_path, sponsorblock_script_path)
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
