# BBS pOpcOrn 🍿

🇫🇷 [Version française](README.md)

Take back control of your YouTube experience — native interface, lightweight playback via MPV, local and privacy-respecting.

If you like the project, a ⭐ on GitHub and a 👍 on [AlternativeTo](https://alternativeto.net/software/bbs-popcorn/about/) make a real difference!

---

## Quick Install (Flatpak)

### 1. Install MPV

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install -y flathub io.mpv.Mpv
```

### 2. Add the BBS pOpcOrn repository

```bash
flatpak remote-add --if-not-exists --from bbs-popcorn \
  https://blacksamdev.github.io/BBS-Popcorn/bbs-popcorn.flatpakrepo
```

### 3. Install

```bash
flatpak install bbs-popcorn io.github.blacksamdev.Popcorn
```

The application will then appear in your desktop menu.

---

## Usage

- **Click on a video** in the YouTube interface to launch it in MPV
- **Quit MPV** : press `q` or close the window — the YouTube window comes back automatically
- **History** : `🕐` button — resumes playback where you left off
- **Comments** : `💬` button — opens the last watched video page to access comments and description
- **Cast** : `📺` button — sends videos to a Chromecast without ads. A control bar appears for pause, volume and releasing the device.
- **Settings** : `⚙` button — quality, window size, SponsorBlock, eco mode

> **Note:** a few seconds delay is normal when launching each video,
> while the stream is being resolved and playback starts.

---

## Update

```bash
flatpak update io.github.blacksamdev.Popcorn
```

---
---

## Technical Documentation

### Installation without Flatpak

System dependencies: `mpv`, `yt-dlp`, `python-gobject`, `webkit2gtk-4.1`

```bash
git clone https://github.com/blacksamdev/BBS-Popcorn.git
cd BBS-Popcorn
make install-deps   # checks and installs Python dependencies
make install-user   # installs in ~/.local
```

System-wide installation:
```bash
sudo make install
```

> **Xorg:** if WebKit displays graphical artifacts, launch with:
> ```bash
> WEBKIT_DISABLE_DMABUF_RENDERER=1 bbs-popcorn
> ```

> **Chromecast cast:** requires `pychromecast` installed on the host:
> ```bash
> pip install pychromecast
> ```

---

### Build from source (Flatpak)

```bash
git clone https://github.com/blacksamdev/BBS-Popcorn.git
cd BBS-Popcorn
sudo flatpak-builder --install --force-clean build-dir io.github.blacksamdev.Popcorn.json
flatpak run io.github.blacksamdev.Popcorn
```

---

### Debug logs

```bash
BBS_POPCORN_DEBUG=1 flatpak run io.github.blacksamdev.Popcorn
tail -f ~/.var/app/io.github.blacksamdev.Popcorn/data/bbs-popcorn/app.log
```

---

### Console messages (harmless)

These messages may appear in the terminal but do not indicate any malfunction:

| Message | Cause | Impact |
|---|---|---|
| `Cannot load libcuda.so.1` | No NVIDIA GPU | None — hardware decoding uses VAAPI |
| `Late SEI is not implemented` | FFmpeg warning on some h264 streams | None — video plays normally |
| `[ipc_0] Write error (Broken pipe)` | MPV closes the IPC connection while loading | None — expected behavior |
| `libEGL warning: MESA-LOADER...` | WebKit/Mesa on some GPU configurations | None — fallback renderer active |

---

### Architecture

```
WebKitGTK (YouTube interface)
    │
    ├── Click on a video
    │
    ├── yt-dlp  →  stream resolution (~2-5s)
    │
    └── MPV  →  video playback
```

---

### License

GPL-3.0 — developed by **blacksamdev** — in tribute to Samuel Bellamy 🏴‍☠️,
the Prince of Pirates, captain of the Whydah.
