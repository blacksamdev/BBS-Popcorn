# BBS Popcorn 🍿

**Client YouTube utilisant MPV comme lecteur externe**

BBS Popcorn est une application Linux qui affiche l’interface web de :contentReference[oaicite:0]{index=0} dans une fenêtre GTK, et permet d’ouvrir les vidéos dans un lecteur externe (MPV).

---

## Fonctionnalités

- Interface YouTube complète (navigation, recherche, connexion Google)
- Ouverture des vidéos via :contentReference[oaicite:1]{index=1}
- Support des diffusions en direct (selon compatibilité)
- Support du décodage matériel (VAAPI, NVDEC selon configuration)
- Gestion locale des cookies de session
- Compatible X11 et Wayland

---

## Prérequis

- Linux (distribution compatible Flatpak)
- Flatpak
- MPV Flatpak (`io.mpv.Mpv`) — installé automatiquement si nécessaire

---

## Installation

### Depuis le repo Flatpak BBS

```bash
flatpak remote-add --if-not-exists bbs-popcorn https://blacksamdev.github.io/BBS-Popcorn/bbs-popcorn.flatpakrepo
flatpak install bbs-popcorn io.github.blacksamdev.Popcorn
```
### Depuis le repo Flatpak BBS

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

### Architecture

WebKitGTK → affichage de l’interface web
        └── ouverture des contenus dans MPV (lecteur externe)
        
Stack technique
| Composant       | Technologie               |
| --------------- | ------------------------- |
| Interface       | Python + GTK4 + WebKitGTK |
| Lecteur         | MPV Flatpak               |
| Résolution flux | yt-dlp                    |
| Cookies         | Stockage local WebKit     |
| Packaging       | Flatpak                   |

### Avertissement légal

Logiciel tiers non officiel
Non affilié, non soutenu par YouTube ou Google
Utilisation soumise aux Conditions d’utilisation de YouTube
Certaines fonctionnalités peuvent ne pas être compatibles avec ces conditions
L’utilisateur est responsable de son usage
Les composants tiers (MPV, yt-dlp) sont indépendants et soumis à leurs propres licences

### Données et confidentialité

Cookies et sessions stockés localement
Aucune donnée transmise à un serveur tiers par défaut
L’utilisateur est responsable de la sécurité de ses identifiants
L’utilisation d’un compte Google dans une application tierce peut présenter des risques
Limitation de responsabilité
Logiciel fourni “en l’état” (GPL-3.0)
Aucune garantie de fonctionnement ou de compatibilité
L’auteur n’est pas responsable des dommages liés à l’utilisation (dans les limites légales)

### Projet

Développé par blacksamdev

### Licence

GPL-3.0
