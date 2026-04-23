from updater import Updater
import sys


def check_dependencies():
    status = Updater.status()

    missing = []

    if not status["mpv"]:
        missing.append("MPV (Flatpak) : flatpak install flathub io.mpv.Mpv")

    if not status["yt-dlp"]:
        missing.append("yt-dlp (système) : apt install yt-dlp")

    if missing:
        print("\n=== Dépendances manquantes ===\n")

        for dep in missing:
            print(" -", dep)

        print("\nInstalle les dépendances puis relance l'application.\n")
        sys.exit(1)


def main():
    print("Popcorn starting...")

    check_dependencies()

    # Exemple d’usage
    url = "https://example.com/video"

    Updater.play(url)


if __name__ == "__main__":
    main()
