from updater import Updater


def main():
    print("Popcorn starting...")

    status = Updater.status()
    print("Dependencies:", status)

    # Exemple d’usage
    url = "https://example.com/video"

    if status["mpv"]:
        Updater.play(url)
    else:
        print("mpv non disponible (fallback flatpak-spawn)")
        Updater.play(url)


if __name__ == "__main__":
    main()
