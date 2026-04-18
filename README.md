BBS Popcorn 🍿

Client YouTube utilisant MPV comme lecteur externe.

BBS Popcorn est une application Linux qui affiche l’interface web de YouTube dans une fenêtre GTK, et permet d’ouvrir les vidéos dans un lecteur externe (MPV).

Fonctionnalités
Interface YouTube complète (navigation, recherche, connexion Google)
Ouverture des vidéos via MPV
Support des diffusions en direct (selon compatibilité)
Support du décodage matériel (VAAPI, NVDEC selon configuration)
Gestion locale des cookies de session
Compatible X11 et Wayland
Prérequis
Linux (distribution compatible Flatpak)
Flatpak
MPV Flatpak (io.mpv.Mpv) — installé automatiquement si nécessaire
Installation
Depuis le repo Flatpak BBS
flatpak remote-add --if-not-exists bbs-popcorn https://blacksamdev.github.io/BBS-Popcorn/bbs-popcorn.flatpakrepo
flatpak install bbs-popcorn io.github.blacksamdev.Popcorn
Mise à jour
flatpak update io.github.blacksamdev.Popcorn
Depuis les sources
git clone https://github.com/blacksamdev/BBS-Popcorn.git
cd BBS-Popcorn
flatpak-builder --user --install --force-clean build-dir io.github.blacksamdev.Popcorn.json
flatpak run io.github.blacksamdev.Popcorn
Architecture

WebKitGTK → affichage de l’interface web
│
└── ouverture des contenus dans MPV (lecteur externe)

Stack technique
Composant	Technologie
Interface	Python + GTK4 + WebKitGTK
Lecteur	MPV Flatpak
Résolution des flux	yt-dlp
Cookies	Stockage local WebKit
Packaging	Flatpak
Avertissement légal
BBS Popcorn est un logiciel tiers non officiel, non affilié, non soutenu et non approuvé par YouTube ni par Google.
L’utilisation du service YouTube via cette application reste soumise aux Conditions d’utilisation de YouTube.
Certaines fonctionnalités du logiciel peuvent ne pas être compatibles avec ces conditions. L’utilisateur est responsable de vérifier la conformité de son usage.
Ce logiciel fournit une interface permettant d’ouvrir des contenus dans un lecteur externe. Il ne prétend pas modifier, contourner ou altérer les mécanismes de diffusion du service utilisé.
Les composants tiers (notamment MPV et yt-dlp) sont indépendants du projet et soumis à leurs propres licences et conditions d’utilisation.
Données et confidentialité
Les données de navigation (cookies, sessions) sont stockées localement via WebKitGTK.
Aucune donnée utilisateur n’est collectée ni transmise à un serveur tiers par BBS Popcorn (sauf comportement contraire introduit par des modifications locales ou des dépendances externes).
L’utilisateur est responsable de la gestion de ses identifiants et de la sécurité de sa session.
L’utilisation d’un compte Google dans une application tierce peut présenter des risques.
Limitation de responsabilité
Le logiciel est fourni “en l’état”, sans garantie d’aucune sorte, conformément à la licence GPL-3.0.
Aucune garantie n’est donnée quant au fonctionnement, à la compatibilité ou à la disponibilité du service.
L’auteur ne pourra être tenu responsable des dommages directs ou indirects résultant de l’utilisation du logiciel, dans les limites autorisées par la loi applicable.
Projet

Développé par blacksamdev.

Licence

GPL-3.0
