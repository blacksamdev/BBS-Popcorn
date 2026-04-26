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
    def run_host(args: list, quiet: bool = False):
        if quiet:
            return subprocess.run(
                ["flatpak-spawn", "--host"] + args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        return subprocess.run(["flatpak-spawn", "--host"] + args)

    @staticmethod
    def popen_host(args: list):
        return subprocess.Popen(["flatpak-spawn", "--host"] + args)

    # ----------------------------
    # MPV
    # ----------------------------
    @staticmethod
    def mpv_available() -> bool:
        # Popcorn targets MPV from Flathub (host side).
        cmd = ["flatpak", "info", "io.mpv.Mpv"]
        result = Updater.run_host(cmd, quiet=True)
        return result.returncode == 0

    @staticmethod
    def play(url: str, cookies_path: str = None):
        process = Updater.start_play(url, cookies_path=cookies_path)
        return process.wait()

    @staticmethod
    def start_play(url: str, cookies_path: str = None):
        cmd = [
            "flatpak",
            "run",
            "io.mpv.Mpv",
            "--ytdl-format=bestvideo+bestaudio/best",
            "--hwdec=auto-safe",
            "--vo=gpu",
            "--gpu-api=opengl",
            "--force-window=yes",
            "--ontop=yes",
            "--volume=100",
        ]
        if cookies_path:
            cmd.append(f"--ytdl-raw-options=cookies={cookies_path}")
        cmd.append(url)
        return Updater.popen_host(cmd)

    # ----------------------------
    # YT-DLP
    # ----------------------------
    @staticmethod
    def ytdlp_available() -> bool:
        return Updater.has_binary("yt-dlp")

    @staticmethod
    def download(url: str):
        # yt-dlp is expected inside this Flatpak runtime.
        return subprocess.run(["yt-dlp", url])

    # ----------------------------
    # Diagnostic
    # ----------------------------
    @staticmethod
    def status():
        return {
            "mpv": Updater.mpv_available(),
            "yt-dlp": Updater.ytdlp_available()
        }


class HostUpdater:
    """
    Minimal compatibility shim for existing app hook.
    """

    def __init__(self, on_done=None):
        self.on_done = on_done

    def check_and_update(self):
        status = Updater.status()
        issues = []

        if not status["mpv"]:
            issues.append("MPV Flatpak manquant: flatpak install flathub io.mpv.Mpv")
        if not status["yt-dlp"]:
            issues.append("yt-dlp introuvable dans l'application")

        if self.on_done:
            if issues:
                self.on_done(" | ".join(issues))
            else:
                self.on_done("Dépendances OK")
