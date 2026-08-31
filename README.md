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

### 4. Recommandé : yt-dlp à jour

```bash
pip install --user --break-system-packages -U yt-dlp
```

YouTube modifie régulièrement ses protections, et le `yt-dlp` embarqué dans le
Flatpak MPV suit le rythme des publications Flathub — il peut donc accumuler du
retard et provoquer des erreurs `403 Forbidden`. Si un `yt-dlp` plus récent est
présent sur votre système, BBS pOpcOrn l'utilise automatiquement à la place.

En cas de blocage sur certaines vidéos, mettez `yt-dlp` à jour puis relancez :
c'est le premier réflexe à avoir, sans attendre de mise à jour de l'application.

---

## Utilisation

- **Cliquer sur une vidéo** dans l'interface YouTube pour la lancer dans MPV
- **Quitter MPV** : touche `q` ou fermer la fenêtre — la fenêtre YouTube revient automatiquement
- **Historique** : bouton `🕐` — reprend la lecture là où vous vous étiez arrêté
- **Commentaires** : bouton `💬` — ouvre la page de la dernière vidéo visionnée pour accéder aux commentaires et à la description
- **Réglages** : bouton `⚙` — qualité, taille de fenêtre, SponsorBlock, langue audio, sous-titres

> **Sous-titres :** la langue audio et les sous-titres sont configurables dans les réglages.
> L'affichage dépend de l'API `timedtext` de YouTube, actuellement instable côté serveur
> (erreurs `429 Too Many Requests` fréquentes, indépendantes de l'application). La piste de
> sous-titres se charge correctement mais son contenu peut ne pas s'afficher selon la
> disponibilité de YouTube. Cette fonction s'améliorera avec les mises à jour de `yt-dlp`.
> Pour de meilleurs résultats, gardez `yt-dlp` à jour sur le host.

> **Note :** un délai de quelques secondes est normal au lancement de chaque vidéo,
> le temps que le flux soit résolu et que la lecture démarre.

> **Diffusion sur TV :** BBS pOpcOrn se concentre sur la lecture locale et n'embarque
> pas de client Chromecast. Pour diffuser sur un téléviseur, utilisez la fonction de
> diffusion de votre navigateur avec le bloqueur de votre choix.

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
