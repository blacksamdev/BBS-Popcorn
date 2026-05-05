# BBS pOpcOrn 🍿

🇫🇷 [Version française](README.md)

**YouTube via MPV**

<p align="center">
  <video src="assets/mon-animation.mp4" width="600" autoplay loop muted playsinline>
</p>

BBS pOpcOrn is a Linux YouTube client based on WebKitGTK.
It displays the YouTube interface in a GTK window and delegates video playback to MPV via streams resolved by yt-dlp.

The goal is to provide a lightweight interface without a full browser, relying on system and user components.

---

## How it works

- YouTube interface via WebKitGTK
- Browsing and search via the official YouTube web interface
- Video playback via MPV (external process)
- Stream resolution via yt-dlp
- Support for playlists and individual videos
- Automatic playback position resume
- Watch history (300 entries, 90 days)
- SponsorBlock integration (toggle in settings)
- Cookie storage via WebKitGTK (local only)

During playback, close the MPV window to return to the YouTube window.

---

## Requirements

- Linux
- Flatpak

---

## Dependencies

Target behaviour for Flatpak:

- MPV must be installed on the host via Flatpak (`io.mpv.Mpv`)
- `yt-dlp` is bundled inside the application (included in the Flatpak build)
- The SponsorBlock script is bundled inside the application

---

## Installing dependencies

### MPV (Flatpak recommended)

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install -y flathub io.mpv.Mpv
```

### yt-dlp

No user installation required: `yt-dlp` is provided inside the pOpcOrn Flatpak.

---

## Installation

Add the Flatpak repository:
```bash
flatpak remote-add --if-not-exists --from bbs-popcorn https://blacksamdev.github.io/BBS-Popcorn/bbs-popcorn.flatpakrepo
```

Install:
```bash
flatpak install bbs-popcorn io.github.blacksamdev.Popcorn
```

---

## Update

```bash
flatpak update io.github.blacksamdev.Popcorn
```

---

## Build from source

```bash
git clone https://github.com/blacksamdev/BBS-Popcorn.git
cd BBS-Popcorn

sudo flatpak-builder --install --force-clean build-dir io.github.blacksamdev.Popcorn.json

flatpak run io.github.blacksamdev.Popcorn
```

---

## Architecture

```
WebKitGTK (YouTube interface)
        │
        ├── user interactions
        │
        ├── yt-dlp (bundled inside pOpcOrn)
        │
        └── MPV (external tool, via IPC socket)
```

---

## Tech stack

| Component | Technology |
|---|---|
| Interface | Python + GTK4 + WebKitGTK |
| Player | MPV (Flatpak) |
| Stream resolution | yt-dlp (bundled inside pOpcOrn) |
| SponsorBlock | mpv_sponsorblock (bundled inside pOpcOrn) |
| Cookies | WebKitGTK local storage |
| Packaging | Flatpak |
| Distribution | GitHub Pages |

---

## Legal notice

- Unofficial third-party software, not affiliated with YouTube or Google
- Use is subject to YouTube's Terms of Service
- The user is responsible for their own usage
- Third-party components (MPV, yt-dlp) are subject to their own licences

---

## Data & privacy

- All data stays local
- Cookies managed by WebKitGTK
- `cookies.sqlite` persists to maintain the YouTube session
- `cookies.txt` is temporarily exported for MPV then deleted at the end of playback
- `resume.json` stores playback position per URL (300 entries, 30 days max)
- `history.json` stores watch history (300 entries, 90 days max)
- No data transmitted to any third party
- No backend server

---

## Settings

From the `⚙` icon in the application:

- Maximum target quality (2160 / 1440 / 1080 / 720 / 480)
- MPV playback mode (windowed / fullscreen)
- MPV window size (%), active in windowed mode only
- SponsorBlock: enable/disable automatic skipping of sponsored segments

From the `🕐` icon:

- Watch history with direct resume playback

---

## Project

Developed by **blacksamdev** — in tribute to Samuel Bellamy 🏴‍☠️,
the Prince of Pirates, captain of the Whydah.

---

## Licence

GPL-3.0
