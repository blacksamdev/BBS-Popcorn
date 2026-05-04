import json
import os
import time

from gi.repository import GLib


_RESUME_FILE = os.path.join(GLib.get_user_data_dir(), "bbs-popcorn", "resume.json")
_MAX_ENTRIES = 300
_MAX_AGE_SECONDS = 30 * 86400   # 30 jours
_MIN_SAVE_SECONDS = 5.0         # ne pas sauvegarder avant 5 s


class ResumeStore:
    """
    Stocke la derniere position de lecture pour chaque URL.
    Limite : 300 entrees max, 30 jours max.
    """

    def __init__(self):
        self.path = _RESUME_FILE
        self._data: dict = {}
        self._load()

    # ─────────────────────────────
    # persistence
    # ─────────────────────────────

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    self._data = loaded
        except Exception:
            self._data = {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._data, f)
        except Exception:
            pass

    # ─────────────────────────────
    # purge
    # ─────────────────────────────

    def _purge(self):
        now = time.time()
        cutoff = now - _MAX_AGE_SECONDS
        self._data = {k: v for k, v in self._data.items() if v.get("ts", 0) >= cutoff}
        if len(self._data) > _MAX_ENTRIES:
            oldest_first = sorted(self._data, key=lambda k: self._data[k].get("ts", 0))
            for k in oldest_first[: len(self._data) - _MAX_ENTRIES]:
                del self._data[k]

    # ─────────────────────────────
    # public API
    # ─────────────────────────────

    def get(self, url: str) -> float | None:
        """Retourne la position sauvegardee pour cette URL, ou None."""
        entry = self._data.get(url)
        if not entry:
            return None
        if time.time() - entry.get("ts", 0) > _MAX_AGE_SECONDS:
            del self._data[url]
            return None
        pos = entry.get("pos")
        return float(pos) if pos is not None else None

    def set(self, url: str, pos: float, duration: float | None = None):
        """
        Sauvegarde la position.
        Ne sauvegarde pas si :
          - pos < 5 s (debut de video)
          - pos >= duree - 30 s ou >= 90 % de la duree (fin de video)
        """
        if pos < _MIN_SAVE_SECONDS:
            self.delete(url)
            return
        if duration and duration > 0:
            if pos >= duration - 30 or pos >= duration * 0.9:
                self.delete(url)
                return
        self._data[url] = {"pos": round(pos, 1), "ts": int(time.time())}
        self._purge()
        self._save()

    def delete(self, url: str):
        if url in self._data:
            del self._data[url]
            self._save()
