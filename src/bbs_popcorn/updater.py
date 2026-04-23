import subprocess


class Updater:
    """
    Gestion propre des dépendances externes Flatpak.
    Mode Flathub-safe : détection + guidance utilisateur.
    """

    MPV_ID = "io.mpv.Mpv"
    YTDLP_ID = "io.github.yt-dlp.yt-dlp"

    # ----------------------------
    # CHECK INSTALLATION
    # ----------------------------
    @staticmethod
    def is_installed(app_id: str) -> bool:
        try:
            subprocess.run(
                ["flatpak", "info", app_id],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    # ----------------------------
    # STATUS GLOBAL
    # ----------------------------
    @staticmethod
    def status():
        return {
            "mpv": Updater.is_installed(Updater.MPV_ID),
            "yt-dlp": Updater.is_installed(Updater.YTDLP_ID)
        }

    # ----------------------------
    # ACTIONS UTILISATEUR
    # ----------------------------
    @staticmethod
    def suggest_install(app_id: str):
        print(f"Dependency missing: {app_id}")
        print("Install with:")
        print(f"  flatpak install flathub {app_id}")

    # ----------------------------
    # PLAY (MPV)
    # ----------------------------
    @staticmethod
    def play(url: str):
        if not Updater.is_installed(Updater.MPV_ID):
            Updater.suggest_install(Updater.MPV_ID)
            return

        subprocess.run([
            "flatpak", "run",
            Updater.MPV_ID,
            url
        ])

    # ----------------------------
    # DOWNLOAD (YT-DLP)
    # ----------------------------
    @staticmethod
    def download(url: str):
        if not Updater.is_installed(Updater.YTDLP_ID):
            Updater.suggest_install(Updater.YTDLP_ID)
            return

        subprocess.run([
            "flatpak", "run",
            Updater.YTDLP_ID,
            url
        ])
