import subprocess
import threading
import shutil
import os


class HostUpdater:
    IN_FLATPAK = os.path.exists("/.flatpak-info")

    def __init__(self, on_done=None):
        self.on_done = on_done

    def check_and_update(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _host_cmd(self, cmd: list) -> list:
        if self.IN_FLATPAK:
            return ["flatpak-spawn", "--host"] + cmd
        return cmd

    def _get_ytdlp_version(self) -> str | None:
        try:
            result = subprocess.run(
                self._host_cmd(["yt-dlp", "--version"]),
                capture_output=True, text=True, timeout=10
            )
            return result.stdout.strip()
        except Exception:
            return None

    def _get_mpv_flatpak_version(self) -> str | None:
        try:
            result = subprocess.run(
                self._host_cmd(["flatpak", "info", "io.mpv.Mpv"]),
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.splitlines():
                if "version" in line.lower():
                    raw = line.split(":")[-1].strip()
                    return raw.lstrip("v")
            return None
        except Exception:
            return None

    def _update_ytdlp(self) -> str:
        print("[updater] Mise à jour yt-dlp...")
        try:
            result = subprocess.run(
                self._host_cmd(["yt-dlp", "-U"]),
                capture_output=True, text=True, timeout=60
            )
            output = result.stdout + result.stderr
            version_after = self._get_ytdlp_version()
            v = f" (v{version_after})" if version_after else ""

            if "up to date" in output.lower() or "à jour" in output.lower():
                return f"yt-dlp : déjà à jour{v}"
            if "updated" in output.lower() or "mis à jour" in output.lower():
                return f"yt-dlp : mis à jour ✓{v}"

            result = subprocess.run(
                self._host_cmd(["pip", "install", "-U", "yt-dlp",
                                "--break-system-packages"]),
                capture_output=True, text=True, timeout=60
            )
            version_after = self._get_ytdlp_version()
            v = f" (v{version_after})" if version_after else ""
            if result.returncode == 0:
                return f"yt-dlp : mis à jour via pip ✓{v}"
            return "yt-dlp : échec mise à jour"

        except Exception as e:
            return f"yt-dlp : erreur ({e})"

    def _update_mpv(self) -> str:
        print("[updater] Vérification mpv Flatpak...")
        check = subprocess.run(
            self._host_cmd(["flatpak", "info", "io.mpv.Mpv"]),
            capture_output=True, text=True, timeout=10
        )

        if check.returncode != 0:
            print("[updater] MPV Flatpak absent, installation...")
            install = subprocess.run(
                self._host_cmd(["flatpak", "install", "-y",
                                "flathub", "io.mpv.Mpv"]),
                capture_output=True, text=True, timeout=300
            )
            if install.returncode == 0:
                version = self._get_mpv_flatpak_version()
                v = f" (v{version})" if version else ""
                return f"mpv Flatpak : installé ✓{v}"
            return "mpv Flatpak : échec installation"

        try:
            result = subprocess.run(
                self._host_cmd(["flatpak", "update", "-y", "io.mpv.Mpv"]),
                capture_output=True, text=True, timeout=120
            )
            output = result.stdout + result.stderr
            if result.returncode != 0:
                return f"mpv Flatpak : erreur ({result.returncode})"

            version_after = self._get_mpv_flatpak_version()
            v = f" (v{version_after})" if version_after else ""

            if "already" in output.lower() or "nothing" in output.lower() \
                    or "up-to-date" in output.lower() or "à jour" in output.lower():
                return f"mpv Flatpak : déjà à jour{v}"
            return f"mpv Flatpak : mis à jour ✓{v}"

        except Exception as e:
            return f"mpv Flatpak : erreur ({e})"

    def _run(self):
        results = []
        results.append(self._update_ytdlp())
        results.append(self._update_mpv())
        msg = "\n".join(results)
        print(f"[updater] {msg}")
        if self.on_done:
            from gi.repository import GLib
            GLib.idle_add(self.on_done, msg)
