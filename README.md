# BBS pOpcOrn 🍿

**YouTube via MPV**

BBS pOpcOrn est un client YouTube Linux basé sur WebKitGTK.
Il affiche l’interface YouTube dans une fenêtre GTK et délègue la lecture vidéo à MPV via des flux résolus par yt-dlp.

L’objectif est de proposer une interface légère sans navigateur complet, en s’appuyant sur des composants système et utilisateurs.

---

## Fonctionnement

- Interface YouTube via WebKitGTK
- Navigation et recherche via l’interface web officielle
- Lecture vidéo via MPV (process externe)
- Résolution des flux via yt-dlp
- Support des playlists et vidéos individuelles
- Stockage des cookies via WebKitGTK (local uniquement)

---

## Prérequis

- Linux
- Flatpak

---

## Dépendances

Comportement cible pour Flatpak/Flathub :

- MPV doit être installé côté hôte via Flatpak (`io.mpv.Mpv`)
- `yt-dlp` est embarqué dans l’application (inclus au build Flatpak)

---

## Installation des dépendances

### MPV (Flatpak recommandé)

Installation :
```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install -y flathub io.mpv.Mpv
```

### yt-dlp

Aucune installation utilisateur nécessaire : `yt-dlp` est fourni dans le Flatpak pOpcOrn.

---

## Installation

Ajouter le dépôt Flatpak :
```bash
flatpak remote-add --if-not-exists bbs-popcorn https://blacksamdev.github.io/BBS-Popcorn/bbs-popcorn.flatpakrepo
```

Installer :
```bash
flatpak install bbs-popcorn io.github.blacksamdev.Popcorn
```

---

## Beta

```bash
flatpak install --or-update ./bbs-popcorn-<version>.flatpak
flatpak run io.github.blacksamdev.Popcorn
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

sudo flatpak-builder --install --force-clean build-dir io.github.blacksamdev.Popcorn.json

flatpak run io.github.blacksamdev.Popcorn
```

---

## Architecture

```
WebKitGTK (interface YouTube)
        │
        ├── interactions utilisateur
        │
        ├── yt-dlp (embarqué dans pOpcOrn)
        │
        └── MPV (outil externe)
```

---

## Stack technique

| Composant | Technologie |
|---|---|
| Interface | Python + GTK4 + WebKitGTK |
| Lecteur | MPV (Flatpak) |
| Résolution flux | yt-dlp (embarqué dans pOpcOrn) |
| Cookies | WebKitGTK stockage local |
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

- Toutes les données restent locales
- Cookies gérés par WebKitGTK
- Aucune transmission à un service tiers
- Aucun serveur backend

---

## Projet

Développé par **blacksamdev** — en hommage à Samuel Bellamy 🏴‍☠️,
le Prince des Pirates, capitaine du Whydah.

---

## Licence

GPL-3.0
