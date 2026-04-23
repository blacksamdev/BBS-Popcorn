import shutil
import subprocess


class Updater:
    """
    Gestion des dépendances externes (mpv / yt-dlp)
    Compatible Flatpak Flathub-ready.
    """

    @staticmethod
    def has_binary(name: str) -> bool:
        return shutil.which(name) is not None

    # ----------------------------
    # MPV
    # ----------------------------
    @staticmethod
    def mpv_available() -> bool:
        return Updater.has_binary("mpv")

    @staticmethod
    def play(url: str):
        if Updater.mpv_available():
            subprocess.run(["mpv", url])
        else:
            subprocess.run(["flatpak-spawn", "--host", "mpv", url])

    # ----------------------------
    # YT-DLP
    # ----------------------------
    @staticmethod
    def ytdlp_available() -> bool:
        return Updater.has_binary("yt-dlp")

    @staticmethod
    def download(url: str):
        if Updater.ytdlp_available():
            subprocess.run(["yt-dlp", url])
        else:
            subprocess.run(["flatpak-spawn", "--host", "yt-dlp", url])

    # ----------------------------
    # Diagnostic (utile debug)
    # ----------------------------
    @staticmethod
    def status():
        return {
            "mpv": Updater.mpv_available(),
            "yt-dlp": Updater.ytdlp_available()
        }
