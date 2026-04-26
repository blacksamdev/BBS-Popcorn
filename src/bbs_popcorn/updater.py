import shutil
import subprocess
import json
import time


class Updater:
    YTDL_FORMATS = {
        "quality": "bestvideo+bestaudio/best",
        "gaming": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    }
    PROFILE_FLAGS = {
        "quality": [],
        "gaming": ["--window-scale=0.8"],
    }

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
    def play(url: str, cookies_path: str = None, playback_profile: str = "gaming"):
        process = Updater.start_play(
            url,
            cookies_path=cookies_path,
            playback_profile=playback_profile
        )
        return process.wait()

    @staticmethod
    def start_play(url: str, cookies_path: str = None, playback_profile: str = "gaming"):
        run_args = ["flatpak", "run"]
        if cookies_path:
            # Allow MPV Flatpak to read exported cookies from this app data path.
            run_args.append(f"--filesystem={cookies_path}:ro")

        ytdl_format = Updater.YTDL_FORMATS.get(playback_profile, Updater.YTDL_FORMATS["gaming"])
        profile_flags = Updater.PROFILE_FLAGS.get(playback_profile, Updater.PROFILE_FLAGS["gaming"])
        cmd = run_args + [
            "io.mpv.Mpv",
            f"--ytdl-format={ytdl_format}",
            "--cookies",
            "--hwdec=auto-safe",
            "--vo=gpu",
            "--gpu-api=opengl",
            "--force-window=yes",
            "--ontop=yes",
            "--volume=100",
        ]
        cmd.extend(profile_flags)
        if cookies_path:
            cmd.append(f"--cookies-file={cookies_path}")
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

    @staticmethod
    def get_upcoming_live_message(url: str):
        if not Updater.ytdlp_available():
            return None

        try:
            result = subprocess.run(
                ["yt-dlp", "--skip-download", "--dump-single-json", url],
                capture_output=True,
                text=True,
                timeout=12
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None

            info = json.loads(result.stdout)
            if info.get("live_status") not in {"is_upcoming", "post_live"}:
                return None

            timestamp = (
                info.get("release_timestamp")
                or info.get("start_time")
                or info.get("timestamp")
            )
            if isinstance(timestamp, (int, float)):
                remaining = int(timestamp - time.time())
                if remaining > 0:
                    minutes = max(1, round(remaining / 60))
                    return f"Live prevu dans environ {minutes} min."

            return "Ce live n'a pas encore commence."
        except Exception:
            return None


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
