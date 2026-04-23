# BBS pOpcOrn 🍿

**YouTube via MPV**

BBS pOpcOrn est un client YouTube Linux basé sur WebKitGTK.  
Il affiche l’interface YouTube dans une fenêtre GTK et redirige la lecture vidéo vers MPV pour une lecture externe optimisée.

L’objectif est de fournir une expérience légère et fluide, sans navigateur complet, en s’appuyant sur des outils externes obligatoires.

---

## Fonctionnement

- Interface YouTube via WebKitGTK
- Navigation et recherche dans l’interface officielle
- Lecture des vidéos via MPV (externe)
- Résolution des flux via yt-dlp (interne)
- Support playlists et vidéos individuelles
- Gestion des cookies de session locale

---

## Prérequis

- Linux
- Flatpak

### Dépendances obligatoires

- MPV : Flatpak (io.mpv.Mpv)
- yt-dlp : gestionnaire de paquets de la distribution

---

## Installation des dépendances

### MPV (Flatpak)

```bash
flatpak install flathub io.mpv.Mpv
```

### yt-dlp : installé sur le système (via apt / dnf / pacman)

Debian / Ubuntu / Mint :
```bash
apt install yt-dlp
```

Fedora :
```bash
dnf install yt-dlp
```

Arch :
```bash
pacman -S yt-dlp
```

---

## Installation

Ajouter le dépôt :
```bash
flatpak remote-add --if-not-exists bbs-popcorn https://blacksamdev.github.io/BBS-Popcorn/bbs-popcorn.flatpakrepo
```

Installer :
```bash
flatpak install bbs-popcorn io.github.blacksamdev.Popcorn
```

---

## Mise à jour

```bash
flatpak update io.github.blacksamdev.Popcorn
```

---

## Installation depuis les sources

```bash
git clone https://github.com/blacksamdev/BBS-Popcorn.git
cd BBS-Popcorn

flatpak-builder --user --install --force-clean build-dir io.github.blacksamdev.Popcorn.json

flatpak run io.github.blacksamdev.Popcorn
```

---

## Architecture

```
WebKitGTK (interface YouTube)
        │
        ├── interactions utilisateur
        │
        ├── yt-dlp (outil interne obligatoire)
        │
        └── MPV (outil externe obligatoire)
```

---

## Stack technique

| Composant | Technologie |
|---|---|
| Interface | Python + GTK4 + WebKitGTK |
| Lecteur | MPV (Flatpak obligatoire) |
| Résolution flux | yt-dlp (système) |
| Cookies | WebKitGTK (stockage local, format navigateur) |
| Packaging | Flatpak |
| Distribution | GitHub Pages |

---

## Avertissement légal

- Logiciel tiers non officiel, non affilié à YouTube ou Google
- Utilisation soumise aux Conditions d'utilisation de YouTube
- L'utilisateur est responsable de son usage
- Les composants tiers (MPV, yt-dlp) sont soumis à leurs propres licences

---

## Données et confidentialité

- Données stockées localement uniquement
- Cookies et sessions stockés localement via WebKitGTK
- Aucune transmission à un serveur tiers
- L'utilisateur est responsable de la sécurité de ses identifiants

---

## Projet

Développé par **blacksamdev** — en hommage à Samuel Bellamy 🏴‍☠️,
le Prince des Pirates, capitaine du Whydah.

---

## Licence

GPL-3.0
