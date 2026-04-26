import os
from datetime import datetime

from gi.repository import GLib


LOG_FILE = os.path.join(GLib.get_user_data_dir(), "bbs-popcorn", "app.log")


def log_event(message: str):
    if not message:
        return

    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as handle:
            handle.write(f"[{timestamp}] {message}\n")
    except Exception:
        # Logging must never break playback flow.
        pass
