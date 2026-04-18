# BBS Popcorn 🍿

**YouTube sans publicité, via MPV.**

BBS Popcorn est un client YouTube Linux qui affiche l'interface YouTube normale dans une fenêtre GTK, mais intercepte chaque clic sur une vidéo pour la lire dans MPV — sans aucune publicité, avec le meilleur format disponible et le décodage hardware.

## Fonctionnalités

- Interface YouTube complète (navigation, recherche, connexion Google)
- Lecture des vidéos via MPV (sans pub)
- Support des lives YouTube
- Décodage hardware automatique (VAAPI, NVDEC)
- Cookies de session persistants
- Mise à jour automatique de MPV et yt-dlp au démarrage
- Compatible X11 et Wayland

## Prérequis

- Linux (toute distribution)
- Flatpak
- MPV Flatpak (`io.mpv.Mpv`) — installé automatiquement au premier lancement

## Installation

### Depuis le repo Flatpak BBS

```bash
flatpak remote-add --if-not-exists bbs-popcorn https://blacksamdev.github.io/BBS-Popcorn/bbs-popcorn.flatpakrepo
flatpak install bbs-popcorn io.github.blacksamdev.Popcorn
```

### Mise à jour

```bash
flatpak update io.github.blacksamdev.Popcorn
```

### Depuis les sources

```bash
git clone https://github.com/blacksamdev/BBS-Popcorn.git
cd BBS-Popcorn
flatpak-builder --user --install --force-clean build-dir io.github.blacksamdev.Popcorn.json
flatpak run io.github.blacksamdev.Popcorn
```

## Architecture
WebKitGTK  →  affiche YouTube normalement
│
└── intercepte les clics vidéo/playlist
│
└── MPV (via Flatpak) joue sans pub

## Stack technique

| Composant | Technologie |
|---|---|
| Interface | Python + GTK4 + WebKitGTK |
| Lecteur | MPV Flatpak |
| Résolution flux | yt-dlp |
| Cookies | SQLite WebKit → Netscape |
| Packaging | Flatpak |

## Projet

Développé par **blacksamdev** — en hommage à Samuel Bellamy 🏴‍☠️, le Prince des Pirates, capitaine du Whydah.

## Licence

GPL-3.0
