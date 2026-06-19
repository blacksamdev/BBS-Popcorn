import os
import shutil
import subprocess
import json
import time

# Détection automatique du mode d'exécution
_IS_FLATPAK = os.path.exists("/app")


class Updater:
    """
    Gestion des dépendances externes (mpv / yt-dlp)
    Compatible Flatpak et installation native.
    """

    PROFILE_FLAGS = {
        "quality": [],
        "gaming": [],
    }
    QUALITY_TARGETS = {"2160", "1440", "1080", "720", "480"}

    # ----------------------------
    # Utils
    # ----------------------------
    @staticmethod
    def has_binary(name: str) -> bool:
        return shutil.which(name) is not None

    @staticmethod
    def _build_cmd(args: list) -> list:
        """Construit la commande selon le mode Flatpak ou natif."""
        if _IS_FLATPAK:
            return ["flatpak-spawn", "--host"] + args
        # Mode natif : remplacer "flatpak run io.mpv.Mpv" par "mpv"
        if "io.mpv.Mpv" in args:
            return ["mpv"] + args[args.index("io.mpv.Mpv") + 1:]
        return args

    @staticmethod
    def run_host(args: list, quiet: bool = False):
        cmd = Updater._build_cmd(args)
        if quiet:
            return subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        return subprocess.run(cmd)

    @staticmethod
    def popen_host(args: list):
        cmd = Updater._build_cmd(args)
        return subprocess.Popen(cmd)

    # ----------------------------
    # MPV
    # ----------------------------
    @staticmethod
    def mpv_available() -> bool:
        cmd = ["flatpak", "info", "io.mpv.Mpv"]
        result = Updater.run_host(cmd, quiet=True)
        return result.returncode == 0

    @staticmethod
    def kill_all_mpv():
        """Tue les process MPV de pOpcOrn côté host, ciblés par le nom du socket."""
        try:
            # Correspond au socket quel que soit son répertoire (/tmp ou /run/user/...)
            Updater.run_host(
                ["pkill", "-f", "bbs-popcorn-mpv.sock"],
                quiet=True
            )
        except Exception:
            pass

    @staticmethod
    def start_play(
        url: str,
        cookies_path: str = None,
        playback_profile: str = "gaming",
        use_fallback_format: bool = False,
        quality_target: str = "1080",
        window_mode: str = "windowed",
        window_scale_percent: int = 80,
        start_pos: float = None,
        ipc_socket_path: str = None,
        monitor_offset: tuple = (0, 0),
        audio_lang: str = "auto",
        subtitle_lang: str = "none",
        subtitle_fallback: bool = False,
    ):
        run_args = ["flatpak", "run"]
        if cookies_path:
            run_args.append(f"--filesystem={cookies_path}:ro")

        if quality_target not in Updater.QUALITY_TARGETS:
            quality_target = "1080"

        if use_fallback_format:
            ytdl_format = (
                f"bestvideo[height<={quality_target}][vcodec^=avc1]+"
                f"bestaudio[acodec^=mp4a]/best[height<={quality_target}]"
            )
        else:
            ytdl_format = (
                f"bestvideo[height<={quality_target}][vcodec^=avc1]+"
                f"bestaudio/best[height<={quality_target}]"
            )

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
            "--title=BBS pOpcOrn - ${media-title}",
            "--volume=100",
            "--msg-level=osd/libass=no",
        ]
        cmd.extend(profile_flags)
        if window_mode == "fullscreen":
            cmd.append("--fullscreen=yes")
        else:
            cmd.append("--fullscreen=no")
            scale = max(50, min(100, int(window_scale_percent))) / 100.0
            cmd.append(f"--window-scale={scale:.2f}")
        if cookies_path:
            cmd.append(f"--cookies-file={cookies_path}")
        if start_pos and start_pos > 0:
            cmd.append(f"--start={start_pos:.1f}")
        if ipc_socket_path:
            cmd.append(f"--input-ipc-server={ipc_socket_path}")
        ox, oy = monitor_offset if monitor_offset else (0, 0)
        cmd.append(f"--geometry=+{ox}+{oy}")

        # Langue audio préférée
        if audio_lang and audio_lang != "auto":
            cmd.append(f"--alang={audio_lang}")

        # Sous-titres : yt-dlp récupère la piste, MPV l'affiche
        if subtitle_lang and subtitle_lang != "none":
            cmd.append(
                f"--ytdl-raw-options=write-subs=,write-auto-subs=,"
                f"sub-langs={subtitle_lang}.*,sub-format=vtt"
            )
            cmd.append(f"--slang={subtitle_lang}")
            cmd.append("--sub-auto=all")
            cmd.append("--sid=1")
            # Secours activé : afficher les sous-titres.
            # Désactivé : piste chargée mais masquée (touche v pour activer).
            if subtitle_fallback:
                cmd.append("--sub-visibility=yes")
            else:
                cmd.append("--sub-visibility=no")

        cmd.append(url)
        _subs = [a for a in cmd if "sub" in a or "slang" in a or "ytdl-raw" in a]
        print("[BBS Popcorn] SUBS FLAGS:", _subs, flush=True)
        return Updater.popen_host(cmd)

    @staticmethod
    def start_idle(
        ipc_socket_path: str,
        cookies_path: str = None,
        quality_target: str = "1080",
        window_mode: str = "windowed",
        window_scale_percent: int = 80,
    ):
        """Lance MPV en mode idle avec un socket IPC pour le pre-warming."""
        if quality_target not in Updater.QUALITY_TARGETS:
            quality_target = "1080"

        ytdl_format = (
            f"bestvideo[height<={quality_target}][vcodec^=avc1]+"
            f"bestaudio/best[height<={quality_target}]"
        )

        run_args = ["flatpak", "run"]
        if cookies_path:
            run_args.append(f"--filesystem={cookies_path}:ro")

        cmd = run_args + [
            "io.mpv.Mpv",
            f"--ytdl-format={ytdl_format}",
            "--cookies",
            "--hwdec=auto-safe",
            "--vo=gpu",
            "--gpu-api=opengl",
            "--force-window=no",
            "--idle=yes",
            f"--input-ipc-server={ipc_socket_path}",
            "--ontop=yes",
            "--title=BBS pOpcOrn - ${media-title}",
            "--volume=100",
            "--msg-level=osd/libass=no",
        ]
        if window_mode == "fullscreen":
            cmd.append("--fullscreen=yes")
        else:
            cmd.append("--fullscreen=no")
            scale = max(50, min(100, int(window_scale_percent))) / 100.0
            cmd.append(f"--window-scale={scale:.2f}")
        if cookies_path:
            cmd.append(f"--cookies-file={cookies_path}")

        return Updater.popen_host(cmd)

    # ----------------------------
    # YT-DLP
    # ----------------------------
    @staticmethod
    def ytdlp_available() -> bool:
        return Updater.has_binary("yt-dlp")

    @staticmethod
    def download(url: str):
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
