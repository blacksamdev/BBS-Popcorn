"""
Internationalisation minimale pour BBS pOpcOrn.
Usage : from bbs_popcorn.i18n import t, set_lang
"""

_LANG = "fr"

_STRINGS = {
    "fr": {
        # Navbar tooltips
        "tooltip_history":      "Historique",
        "tooltip_comments":     "Voir les commentaires de la dernière vidéo visionnée",
        "tooltip_settings":     "Réglages",

        # Popover historique
        "history_title":        "Historique",
        "history_clear":        "Effacer",
        "history_empty":        "Aucun historique.",

        # Popover réglages
        "settings_quality":     "Qualité max :",
        "settings_window":      "Mode fenêtre :",
        "settings_window_w":    "Fenêtre",
        "settings_window_fs":   "Plein écran",
        "settings_size":        "Taille : {value}%",
        "settings_sponsorblock":"SponsorBlock :",
        "settings_sb_na":       "Script SponsorBlock non disponible dans ce build.",
        "settings_webkit":      "Mode WebKit :",
        "settings_webkit_n":    "Mode normal",
        "settings_webkit_eco":  "Mode éco",
        "settings_eco_tooltip": (
            "Mode éco : réduit le fonctionnement de WebKit au minimum.\n"
            "WebGL et WebAudio désactivés dans le navigateur intégré.\n"
            "Les Shorts sont lus par MPV au lieu du navigateur intégré."
        ),
        "settings_help": (
            "Lecture externe : la vidéo s'ouvre dans MPV.\n"
            "Pour revenir à YouTube, fermez la fenêtre MPV."
        ),
        "settings_save":        "Enregistrer",
        "settings_language":    "Langue :",
        "lang_restart":         "Effectif au prochain lancement.",

        # Overlay chargement
        "loading":              "Chargement de la vidéo...",

        # Status bar
        "status_ready":         "Prêt.",
        "status_preparing":     "Préparation de la lecture...",
        "status_resume":        "Reprise à {time}...",
        "status_playing":       "Lecture en cours.",
        "status_done":          "Lecture terminée.",
        "status_done_warn":     "Lecture terminée avec avertissement.",
        "status_failed":        "Impossible de lancer la lecture.",
        "status_unavailable":   "Vidéo indisponible.",
        "status_blocked":       "Navigation hors YouTube bloquée.",
        "status_compat":        "Format compatible : nouvelle tentative...",
    },

    "en": {
        # Navbar tooltips
        "tooltip_history":      "History",
        "tooltip_comments":     "View comments from the last watched video",
        "tooltip_settings":     "Settings",

        # History popover
        "history_title":        "History",
        "history_clear":        "Clear",
        "history_empty":        "No history.",

        # Settings popover
        "settings_quality":     "Max quality:",
        "settings_window":      "Window mode:",
        "settings_window_w":    "Window",
        "settings_window_fs":   "Fullscreen",
        "settings_size":        "Size: {value}%",
        "settings_sponsorblock":"SponsorBlock:",
        "settings_sb_na":       "SponsorBlock script not available in this build.",
        "settings_webkit":      "WebKit mode:",
        "settings_webkit_n":    "Normal mode",
        "settings_webkit_eco":  "Eco mode",
        "settings_eco_tooltip": (
            "Eco mode: reduces WebKit resource usage.\n"
            "WebGL and WebAudio disabled in the embedded browser.\n"
            "Shorts are played by MPV instead of the browser."
        ),
        "settings_help": (
            "External playback: the video opens in MPV.\n"
            "To return to YouTube, close the MPV window."
        ),
        "settings_save":        "Save",
        "settings_language":    "Language:",
        "lang_restart":         "Effective on next launch.",

        # Loading overlay
        "loading":              "Loading video...",

        # Status bar
        "status_ready":         "Ready.",
        "status_preparing":     "Preparing playback...",
        "status_resume":        "Resuming at {time}...",
        "status_playing":       "Now playing.",
        "status_done":          "Playback finished.",
        "status_done_warn":     "Playback finished with warning.",
        "status_failed":        "Unable to start playback.",
        "status_unavailable":   "Video unavailable.",
        "status_blocked":       "Navigation outside YouTube blocked.",
        "status_compat":        "Compatible format: retrying...",
    },
}


def set_lang(lang: str):
    global _LANG
    if lang in _STRINGS:
        _LANG = lang


def t(key: str, **kwargs) -> str:
    """Retourne la chaîne traduite. Supporte les placeholders {value}, {time}..."""
    s = _STRINGS.get(_LANG, _STRINGS["fr"]).get(key)
    if s is None:
        s = _STRINGS["fr"].get(key, key)
    if kwargs:
        try:
            return s.format(**kwargs)
        except (KeyError, ValueError):
            return s
    return s
