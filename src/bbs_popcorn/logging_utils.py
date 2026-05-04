import os
from datetime import datetime

from gi.repository import GLib


LOG_FILE = os.path.join(GLib.get_user_data_dir(), "bbs-popcorn", "app.log")
LOG_FILE_OLD = LOG_FILE + ".old"
LOG_MAX_BYTES = 500 * 1024   # 500 KB
DEBUG_LOG_ENABLED = os.environ.get("BBS_POPCORN_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _rotate_if_needed():
    try:
        if os.path.getsize(LOG_FILE) >= LOG_MAX_BYTES:
            if os.path.exists(LOG_FILE_OLD):
                os.remove(LOG_FILE_OLD)
            os.rename(LOG_FILE, LOG_FILE_OLD)
    except OSError:
        pass


def log_event(message: str, level: str = "info"):
    if not message:
        return
    if level == "debug" and not DEBUG_LOG_ENABLED:
        return

    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        _rotate_if_needed()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as handle:
            handle.write(f"[{timestamp}] [{level.upper()}] {message}\n")
    except Exception:
        # Logging must never break playback flow.
        pass
