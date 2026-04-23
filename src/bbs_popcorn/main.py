from updater import Updater


def main():
    print("Popcorn starting...")

    status = Updater.status()
    print("Dependencies:", status)

    url = "https://example.com/video"

    if not status["mpv"]:
        Updater.suggest_install(Updater.MPV_ID)

    if not status["yt-dlp"]:
        Updater.suggest_install(Updater.YTDLP_ID)

    if status["mpv"]:
        Updater.play(url)


if __name__ == "__main__":
    main()
