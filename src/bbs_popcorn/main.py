#!/usr/bin/env python3

import os
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")

from gi.repository import GLib
from bbs_popcorn.app import YtMpvApp


def main():
    data_dir = os.path.join(GLib.get_user_data_dir(), "bbs-popcorn")
    cache_dir = os.path.join(GLib.get_user_cache_dir(), "bbs-popcorn")

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)

    cookie_db_path = os.path.join(data_dir, "cookies.sqlite")
    cookie_export_path = os.path.join(cache_dir, "yt-cookies.txt")

    app = YtMpvApp(cookie_db_path, cookie_export_path)
    app.run(None)


if __name__ == "__main__":
    main()
