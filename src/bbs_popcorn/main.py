from updater import Updater
import sys


def check_dependencies():
    status = Updater.status()

    missing = []

    if not status.get("mpv", False):
        missing.append("MPV (Flatpak) : flatpak install flathub io.mpv.Mpv")

    if not status.get("yt-dlp", False):
        missing.append("yt-dlp (système) : apt/dnf/pacman install yt-dlp")

    if missing:
        print("\n=== Dépendances manquantes ===\n")

        for dep in missing:
            print(" -", dep)

        print("\nInstalle les dépendances puis relance l'application.\n")
        sys.exit(1)


def main():
    print("Popcorn starting...")

    check_dependencies()

    # URL test (à remplacer par WebKit callback dans ton app réelle)
    url = "https://example.com/video"

    try:
        Updater.play(url)
    except Exception as e:
        print("Erreur lecture vidéo :", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
