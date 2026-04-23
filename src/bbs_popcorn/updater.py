import shutil
import subprocess


class Updater:
    """
    Gestion des dépendances externes (mpv / yt-dlp)
    Compatible Flatpak (host fallback via flatpak-spawn).
    """

    # ----------------------------
    # Utils
    # ----------------------------
    @staticmethod
    def has_binary(name: str) -> bool:
        return shutil.which(name) is not None

    @staticmethod
    def run_host(args: list):
        return subprocess.run(["flatpak-spawn", "--host"] + args)

    # ----------------------------
    # MPV
    # ----------------------------
    @staticmethod
    def mpv_available() -> bool:
        return Updater.has_binary("mpv")

    @staticmethod
    def play(url: str):
        if Updater.mpv_available():
            return subprocess.run(["mpv", url])

        return Updater.run_host(["mpv", url])

    # ----------------------------
    # YT-DLP
    # ----------------------------
    @staticmethod
    def ytdlp_available() -> bool:
        return Updater.has_binary("yt-dlp")

    @staticmethod
    def download(url: str):
        if Updater.ytdlp_available():
            return subprocess.run(["yt-dlp", url])

        return Updater.run_host(["yt-dlp", url])

    # ----------------------------
    # Diagnostic
    # ----------------------------
    @staticmethod
    def status():
        return {
            "mpv": Updater.mpv_available(),
            "yt-dlp": Updater.ytdlp_available()
        }
