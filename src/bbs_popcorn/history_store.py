import json
import os
import time

from gi.repository import GLib


_HISTORY_FILE = os.path.join(GLib.get_user_data_dir(), "bbs-popcorn", "history.json")
_MAX_ENTRIES = 300
_MAX_AGE_SECONDS = 90 * 86400   # 90 jours


class HistoryStore:
    """
    Stocke l'historique des URLs jouees.
    Limite : 300 entrees max, 90 jours max.
    Les doublons sont dedupes (une URL = une entree, la plus recente gagne).
    """

    def __init__(self):
        self.path = _HISTORY_FILE
        self._data: list = []   # liste de {url, title, ts}, ordre chronologique
        self._load()

    # ─────────────────────────────
    # persistence
    # ─────────────────────────────

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, list):
                    self._data = loaded
        except Exception:
            self._data = []

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
        cutoff = time.time() - _MAX_AGE_SECONDS
        self._data = [e for e in self._data if e.get("ts", 0) >= cutoff]
        if len(self._data) > _MAX_ENTRIES:
            self._data = self._data[-_MAX_ENTRIES:]

    # ─────────────────────────────
    # public API
    # ─────────────────────────────

    def add(self, url: str, title: str = ""):
        """Ajoute une entree. Dedupe par URL (la plus recente remplace l'ancienne)."""
        self._data = [e for e in self._data if e.get("url") != url]
        self._data.append({
            "url": url,
            "title": title.strip() if title.strip() else url,
            "ts": int(time.time()),
        })
        self._purge()
        self._save()

    def entries(self) -> list:
        """Retourne les entrees, la plus recente en premier."""
        return list(reversed(self._data))

    def clear(self):
        self._data = []
        self._save()
