import os
import sys
import shutil
from gi.repository import GLib

from bbs_popcorn.app import YtMpvApp

# Bundled script location inside the Flatpak.
_BUNDLED_SPONSORBLOCK = "/app/share/bbs-popcorn/sponsorblock.lua"


def main():
    GLib.set_prgname("bbs-popcorn")
    GLib.set_application_name("BBS pOpcOrn")
    print("Popcorn starting...")

    state_dir = os.path.join(GLib.get_user_data_dir(), "bbs-popcorn")
    os.makedirs(state_dir, mode=0o700, exist_ok=True)
    try:
        os.chmod(state_dir, 0o700)
    except OSError:
        pass

    cookie_db_path = os.path.join(state_dir, "cookies.sqlite")
    cookie_export_path = os.path.join(state_dir, "cookies.txt")

    # Copy the bundled SponsorBlock script + shared dir to state_dir so MPV
    # Flatpak can access them via _sync_sponsorblock in player.py.
    sponsorblock_script_path = None
    dest = os.path.join(state_dir, "sponsorblock.lua")
    shared_src = "/app/share/bbs-popcorn/sponsorblock_shared"
    shared_dest = os.path.join(state_dir, "sponsorblock_shared")

    if os.path.exists(_BUNDLED_SPONSORBLOCK):
        try:
            if not os.path.exists(dest) or (
                os.path.getmtime(_BUNDLED_SPONSORBLOCK) > os.path.getmtime(dest)
            ):
                shutil.copy2(_BUNDLED_SPONSORBLOCK, dest)
                os.chmod(dest, 0o600)
            if os.path.isdir(shared_src):
                if os.path.exists(shared_dest):
                    shutil.rmtree(shared_dest)
                shutil.copytree(shared_src, shared_dest)
                for f in os.listdir(shared_dest):
                    try:
                        os.chmod(os.path.join(shared_dest, f), 0o600)
                    except OSError:
                        pass
            sponsorblock_script_path = dest
        except OSError:
            pass

    app = YtMpvApp(cookie_db_path, cookie_export_path, sponsorblock_script_path)
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
