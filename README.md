# BBS pOpcOrn 🍿

🇬🇧 [English version](README.en.md)

Reprenez le contrôle de votre expérience YouTube — interface native, lecture légère via MPV, locale et respectueuse de votre vie privée.

Si le projet vous plaît, une ⭐ GitHub et un 👍 sur [AlternativeTo](https://alternativeto.net/software/bbs-popcorn/about/) font vraiment la différence !

---

## Installation rapide (Flatpak)

### 1. Installer MPV

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install -y flathub io.mpv.Mpv
```

### 2. Ajouter le dépôt BBS pOpcOrn

```bash
flatpak remote-add --if-not-exists --from bbs-popcorn \
  https://blacksamdev.github.io/BBS-Popcorn/bbs-popcorn.flatpakrepo
```

### 3. Installer

```bash
flatpak install bbs-popcorn io.github.blacksamdev.Popcorn
```

L'application apparaît ensuite dans le menu de votre bureau.

---

## Utilisation

- **Cliquer sur une vidéo** dans l'interface YouTube pour la lancer dans MPV
- **Quitter MPV** : touche `q` ou fermer la fenêtre — la fenêtre YouTube revient automatiquement
- **Historique** : bouton `🕐` — reprend la lecture là où vous vous étiez arrêté
- **Commentaires** : bouton `💬` — ouvre la page de la dernière vidéo visionnée pour accéder aux commentaires et à la description
- **Cast** : bouton `📺` — envoie les vidéos sur un Chromecast sans publicité. Une barre de contrôle apparaît pour pause, volume et libérer l'appareil.
- **Réglages** : bouton `⚙` — qualité, taille de fenêtre, SponsorBlock, mode éco

> **Note :** un délai de quelques secondes est normal au lancement de chaque vidéo,
> le temps que le flux soit résolu et que la lecture démarre.

---

## Mise à jour

```bash
flatpak update io.github.blacksamdev.Popcorn
```

---
---

## Documentation technique

### Installation sans Flatpak

Dépendances système : `mpv`, `yt-dlp`, `python-gobject`, `webkit2gtk-4.1`

```bash
git clone https://github.com/blacksamdev/BBS-Popcorn.git
cd BBS-Popcorn
make install-deps   # vérifie et installe les dépendances Python
make install-user   # installe dans ~/.local
```

Installation système :
```bash
sudo make install
```

> **Xorg :** si WebKit affiche des artefacts graphiques, lancer avec :
> ```bash
> WEBKIT_DISABLE_DMABUF_RENDERER=1 bbs-popcorn
> ```

> **Cast Chromecast :** nécessite `pychromecast` installé sur le host :
> ```bash
> pip install pychromecast
> ```

---

### Build depuis les sources (Flatpak)

```bash
git clone https://github.com/blacksamdev/BBS-Popcorn.git
cd BBS-Popcorn
sudo flatpak-builder --install --force-clean build-dir io.github.blacksamdev.Popcorn.json
flatpak run io.github.blacksamdev.Popcorn
```

---

### Logs de debug

```bash
BBS_POPCORN_DEBUG=1 flatpak run io.github.blacksamdev.Popcorn
tail -f ~/.var/app/io.github.blacksamdev.Popcorn/data/bbs-popcorn/app.log
```

---

### Messages dans la console (normaux)

Ces messages apparaissent dans le terminal mais n'indiquent aucun dysfonctionnement :

| Message | Cause | Impact |
|---|---|---|
| `Cannot load libcuda.so.1` | Pas de GPU NVIDIA | Aucun — décodage matériel via VAAPI |
| `Late SEI is not implemented` | Avertissement FFmpeg sur certains flux h264 | Aucun — vidéo normale |
| `[ipc_0] Write error (Broken pipe)` | MPV ferme la connexion IPC en chargeant | Aucun — comportement normal |
| `libEGL warning: MESA-LOADER...` | WebKit/Mesa sur certaines configurations GPU | Aucun — rendu de secours actif |

---

### Architecture

```
WebKitGTK (interface YouTube)
    │
    ├── Clic sur une vidéo
    │
    ├── yt-dlp  →  résolution du flux (~2-5s)
    │
    └── MPV  →  lecture vidéo
```

---

### Licence

GPL-3.0 — développé par **blacksamdev** — en hommage à Samuel Bellamy 🏴‍☠️,
le Prince des Pirates, capitaine du Whydah.
