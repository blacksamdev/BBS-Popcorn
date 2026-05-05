# BBS pOpcOrn 🍿

🇬🇧 [English version](README.en.md)

**YouTube via MPV**

<p align="center">
  <video src="assets/mon-animation.mp4" width="600" autoplay loop muted playsinline>
</p>

BBS pOpcOrn est un client YouTube Linux basé sur WebKitGTK.
Il affiche l'interface YouTube dans une fenêtre GTK et délègue la lecture vidéo à MPV via des flux résolus par yt-dlp.

L'objectif est de proposer une interface légère sans navigateur complet, en s'appuyant sur des composants système et utilisateurs.

---

## Fonctionnement

- Interface YouTube via WebKitGTK
- Navigation et recherche via l'interface web officielle
- Lecture vidéo via MPV (process externe)
- Résolution des flux via yt-dlp
- Support des playlists et vidéos individuelles
- Reprise automatique de la position de lecture
- Historique des vidéos jouées (300 entrées, 90 jours)
- SponsorBlock intégré (activable dans les réglages)
- Stockage des cookies via WebKitGTK (local uniquement)

Pendant la lecture, fermez la fenêtre MPV pour revenir à la fenêtre YouTube.

---

## Prérequis

- Linux
- Flatpak

---

## Dépendances

Comportement cible pour Flatpak/Flathub :

- MPV doit être installé côté hôte via Flatpak (`io.mpv.Mpv`)
- `yt-dlp` est embarqué dans l'application (inclus au build Flatpak)
- Le script SponsorBlock est embarqué dans l'application

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
flatpak remote-add --if-not-exists --from bbs-popcorn https://blacksamdev.github.io/BBS-Popcorn/bbs-popcorn.flatpakrepo
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
        └── MPV (outil externe, via IPC socket)
```

---

## Stack technique

| Composant | Technologie |
|---|---|
| Interface | Python + GTK4 + WebKitGTK |
| Lecteur | MPV (Flatpak) |
| Résolution flux | yt-dlp (embarqué dans pOpcOrn) |
| SponsorBlock | mpv_sponsorblock (embarqué dans pOpcOrn) |
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
- `cookies.sqlite` reste persistant pour conserver la session YouTube
- `cookies.txt` est exporté temporairement pour MPV puis supprimé en fin de lecture
- `resume.json` stocke la position de reprise par URL (300 entrées, 30 jours max)
- `history.json` stocke l'historique des vidéos jouées (300 entrées, 90 jours max)
- Aucune transmission à un service tiers
- Aucun serveur backend

---

## Réglages

Depuis l'icône `⚙` de l'application :

- Qualité max cible (2160 / 1440 / 1080 / 720 / 480)
- Mode de lecture MPV (fenêtre / plein écran)
- Taille fenêtre MPV (%), active uniquement en mode fenêtré
- SponsorBlock : active/désactive le saut automatique des segments sponsorisés

Depuis l'icône `🕐` :

- Historique des vidéos jouées avec reprise directe

---

## Projet

Développé par **blacksamdev** — en hommage à Samuel Bellamy 🏴‍☠️,
le Prince des Pirates, capitaine du Whydah.

---

## Licence

GPL-3.0
