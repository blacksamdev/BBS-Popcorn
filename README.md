# BBS Popcorn 🍿

**YouTube, via MPV.**

BBS Popcorn est un client YouTube Linux qui affiche l'interface YouTube normale dans une fenêtre GTK et intercepte chaque clic sur une vidéo ou une playlist pour la lire dans MPV — avec le meilleur format disponible et le décodage hardware.
En utilisant MPV comme lecteur externe, BBS Popcorn offre une lecture plus fluide et beaucoup plus légère qu’un navigateur, tout en profitant du décodage matériel natif.

---

## Fonctionnalités

- Interface YouTube complète (navigation, recherche, connexion Google)
- Lecture des vidéos et playlists via MPV (lecteur vidéo externe)
- Support des lives YouTube
- Décodage hardware automatique (VAAPI, NVDEC)
- Cookies de session persistants
- Mise à jour automatique de MPV et yt-dlp au démarrage
- Compatible X11 et Wayland

---

## Prérequis

- Linux (toute distribution)
- Flatpak
- MPV Flatpak (`io.mpv.Mpv`) — installé automatiquement au premier lancement

---

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

---

## Architecture
```
WebKitGTK  →  affiche YouTube normalement
     │
     └── intercepte les clics vidéo/playlist
               │
               └── MPV (via Flatpak) joue le contenu
```
---

## Stack technique

| Composant | Technologie |
|---|---|
| Interface | Python + GTK4 + WebKitGTK |
| Lecteur | MPV Flatpak |
| Résolution flux | yt-dlp |
| Cookies | SQLite WebKit → Netscape |
| Packaging | Flatpak |

---

## Avertissement légal

- Logiciel tiers non officiel, non affilié à YouTube ou Google
- Utilisation soumise aux Conditions d'utilisation de YouTube
- L'utilisateur est responsable de son usage
- Les composants tiers (MPV, yt-dlp) sont soumis à leurs propres licences

---

## Données et confidentialité

- Cookies et sessions stockés localement uniquement
- Aucune donnée transmise à un serveur tiers
- L'utilisateur est responsable de la sécurité de ses identifiants

---

## Projet

Développé par **blacksamdev** — en hommage à Samuel Bellamy 🏴‍☠️,
le Prince des Pirates, capitaine du Whydah.

## Licence

GPL-3.0
