# QA Checklist (manuel)

## Parcours de base

- [ ] Lancer l'application: `flatpak run io.github.blacksamdev.Popcorn`
- [ ] Vérifier que l'interface YouTube s'affiche correctement
- [ ] Vérifier que la barre d'etat s'actualise (pret, preparation, lecture)

## Lecture video MPV

- [ ] Clic sur video classique -> MPV se lance
- [ ] Fermer MPV -> retour automatique sur la fenetre YouTube
- [ ] Vérifier que le titre MPV contient l'aide de retour
- [ ] Vérifier qu'une video suivante peut se lancer sans relancer l'app

## Shorts (WebKit)

- [ ] Ouvrir un short et vérifier le son
- [ ] Vérifier qu'aucun comportement audio parasite n'apparait

## Playlist et live

- [ ] Ouvrir une playlist et vérifier la lecture
- [ ] Ouvrir un live programmé et vérifier le message "live prévu"

## Options ⚙

- [ ] Changer qualité max (ex: 1080 -> 720) et vérifier prise en compte
- [ ] Changer priorité (plus haute / plus basse) et vérifier prise en compte
- [ ] Passer en plein écran puis vérifier que le slider % est désactivé
- [ ] Repasser en mode fenêtré puis vérifier slider % réactivé
- [ ] Vérifier persistance des options après redémarrage de l'app

## Sécurité cookies

- [ ] Vérifier que `cookies.sqlite` existe après login
- [ ] Lancer une lecture MPV puis vérifier suppression de `cookies.txt` à la fin
- [ ] Vérifier droits restrictifs sur les fichiers/dossier de state

## Logs

- [ ] Vérifier création de `~/.local/share/bbs-popcorn/app.log`
- [ ] Vérifier présence d'entrées utiles (lecture, erreurs)
- [ ] Vérifier mode debug: `BBS_POPCORN_DEBUG=1 flatpak run io.github.blacksamdev.Popcorn`
