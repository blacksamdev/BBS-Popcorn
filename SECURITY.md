# Politique de securite

## Versions supportees

Les correctifs de securite sont appliques sur la branche `main`.
Les builds beta sont maintenus en best-effort pendant la phase de test.

## Signaler une vulnerabilite

Si vous decouvrez une vulnerabilite de securite dans BBS Popcorn, merci de la signaler en prive.

N'ouvrez **pas** d'issue publique GitHub pour un probleme de securite.

Utilisez plutot les advisories prives GitHub :
[https://github.com/blacksamdev/BBS-Popcorn/security/advisories/new](https://github.com/blacksamdev/BBS-Popcorn/security/advisories/new)

Merci d'inclure :
- les etapes de reproduction
- la version ou le commit affecte
- l'impact potentiel

Nous accusons reception rapidement, puis nous investiguons et coordonnons une divulgation responsable une fois le correctif disponible.

## Perimetre du projet

Dans le perimetre :
- `src/` (code Python de l'application)
- `io.github.blacksamdev.Popcorn.json` (manifest Flatpak)
- `.github/workflows/` (pipeline packaging et publication)

Hors perimetre :
- vulnerabilites des composants tiers (`mpv`, `yt-dlp`, `WebKitGTK`, runtime GNOME)
- problemes de configuration locale hors projet

Pour les composants tiers, merci de signaler directement au projet amont concerne.
