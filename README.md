# Studio Vidéo

Moteur de production vidéo utilisé par le skill Claude « Studio Vidéo ».
Entrées : un dossier de rushes, un script, un style et une composition. Sortie : une vidéo
montée, contrôlée, avec la liste des plans utilisés.

## Installation (dans une session Claude)

```bash
git clone --depth 1 https://github.com/contact190/studio-video
cd studio-video && bash setup.sh --voice
```

## Le parcours

| Étape | Qui | Commande |
|---|---|---|
| 1. Indexer les rushes (seuls les nouveaux sont analysés) | moteur | `python3 engine/index_rushes.py <dossier>` |
| 2. Regarder les planches et décrire les segments | Claude | `python3 engine/annotate.py <index> apply annotations.json` |
| 3. Écrire le plan de montage à partir du script | Claude | voir `docs/plan.md` |
| 4. Aperçu rapide, puis rendu final | moteur | `python3 engine/build.py plan.json [--preview]` |
| 5. Contrôle qualité | moteur + Claude | `python3 engine/check.py <video.mp4>` |

## La bibliothèque

- `library/styles/` : le style de montage (sous-titres, étiquettes, image, rythme, musique, carton final)
- `library/compositions/` : la structure en cases (rôle, durée, type de voix)
- `library/brand/` : la marque (couleur d'accent, logo, appel à l'action) ; les valeurs `brand.xxx` d'un style y renvoient

Chaque fiche a un `version` et un `status` (`brouillon` puis `validé`). Une modification validée
en mode Atelier crée une nouvelle version et un commit : on peut revenir en arrière.

## Organisation

```
engine/   index_rushes.py  annotate.py  build.py  check.py  tts.py  music.py  common.py
render/   modèle de montage Remotion (src/Edit.jsx)
library/  styles/  compositions/  brand/
tts/      mots ajoutés au dictionnaire de la voix off
docs/     plan.md : format du plan de montage
```

## Installer le skill

- **App Claude (web, ordinateur, mobile)** : Customize › Skills › + › Create skill › Upload a skill, avec `studio-video-skill.zip` (le dossier `skills/studio-video` zippé).
- **Claude Code (terminal)** : `npx skills add contact190/studio-video --skill studio-video --agent claude-code -g`
  (dépôt privé : être invité sur GitHub et connecté avec `gh auth login` avant).
