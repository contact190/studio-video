---
name: studio-video
description: Produire une vidéo montée à partir d'un dossier de rushes et d'un script, avec un style et une composition prédéfinis (moteur GitHub contact190/studio-video, rea-video, Whisper, Remotion). Inclut le mode Atelier pour créer, modifier ou valider un style ou une composition.
---

# Studio Vidéo

L'utilisateur donne **deux choses** : un dossier de rushes et un script. Le reste vient de la
bibliothèque. Ne pose aucune autre question tant que ces deux entrées suffisent ; annonce en une
ligne le style, la composition et le format retenus, puis travaille.

| Entrée | Obligatoire | Par défaut |
|---|---|---|
| Dossier de rushes | oui | — |
| Script (Google Doc, fichier ou texte) | oui | — |
| Style, composition, format, marque | non | `library/defaults.json` |

Le code et la bibliothèque vivent dans le dépôt `contact190/studio-video` ; les rushes et les
vidéos finies dans `G:\Mon Drive\STUDIO VIDÉO` sur l'ordinateur de l'utilisateur (Google Drive
pour ordinateur), atteint par le pont de l'app Claude. Le connecteur Drive ne télécharge pas au-delà
de 10 Mo : ne jamais l'utiliser pour des vidéos, seulement pour lire le script.

## Installation (une seule fois par utilisateur)

Chaque utilisateur a **son** Drive et **sa** videoask : l'installation se fait une fois par
utilisateur, dans ses comptes. Elle se lance seule au premier usage ; l'utilisateur n'a rien à
préparer.

Avant tout : si `Réglages` du sheet PILOTAGE de l'utilisateur contient déjà l'URL du script VideoAsk,
ou si son dossier `STUDIO VIDÉO` existe, l'installation est faite : ne rien refaire, ne pas en parler.
S'il n'utilise pas VideoAsk, ne faire que l'étape 1.

Sinon, Claude fait tout lui-même et ne demande que **deux clics** à l'utilisateur, en lui envoyant
exactement le message ci-dessous au bon moment (ne jamais taper de mot de passe à sa place) :

> **Une seule action de ta part :** dans l'onglet Apps Script, clique sur **Autoriser l'accès**,
> choisis ton compte Google, puis **Paramètres avancés › Accéder à Studio Vidéo — VideoAsk ›
> Autoriser**. C'est ton propre script ; Google affiche cet avertissement pour tout script
> personnel. Ensuite écris « c'est fait ».

1. **Dossiers Drive** (connecteur Google Drive, sinon navigateur) : `STUDIO VIDÉO/BIBLIOTHÈQUE/{RUSHES,SONS,RÉFÉRENCES}`,
   `STUDIO VIDÉO/SORTIES`, `STUDIO VIDÉO/TEST`. Noter l'ID de `RUSHES`.
2. **VideoAsk → Drive** (gratuit, jusqu'à 50 Mo par vidéo ; Make gratuit refuse plus de 5 Mo) :
   `python3 integrations/fill_gs.py <ID RUSHES>` ; navigateur : `script.google.com/create`, nommer
   « Studio Vidéo — VideoAsk », coller le code (`monaco.editor.getModels()[0].setValue(code)`),
   enregistrer ; Déployer › Nouveau déploiement › Application Web (moi ; tout le monde) › Déployer ;
   envoyer le message ci-dessus ; copier l'URL `/exec`. Si la fenêtre Google est bloquée par le
   navigateur intégré, donner le lien du projet à ouvrir dans Chrome.
3. **Webhook VideoAsk** (navigateur, organisation qui contient la videoask) : videoask › Connect ›
   Webhooks › `<URL /exec>?k=<clé>`, événement `form_response`. Demander l'accord avant d'enregistrer.
   Sans plan payant VideoAsk (pas de webhooks) : export zip une fois (Télécharger › Media files).
4. Test : « Send a test response » ouvre la videoask publique ; l’utilisateur y enregistre une courte réponse (ou attendre une vraie réponse) : un fichier `Nom_AAAA-MM-JJ_HHmm_Qnn.mp4` arrive dans RUSHES.
5. Écrire dans `Réglages` : ID des dossiers, URL du script, videoask branchée.

## 0. Démarrage (chaque session)

1. `add_repo` contact190/studio-video (accès push), puis `git clone --depth 1` dans `/home/claude/studio-video`.
2. Lancer en arrière-plan : `bash setup.sh --voice --rea` (modèles dans `/tmp/studio-models`, rea-video dans `/tmp/rea-video`). Avancer sur les étapes 1 et 3 pendant l'installation.
3. Lire `library/defaults.json`, la fiche de style et la fiche de composition choisies.

## 1. Rapatrier les rushes

1. `get_device_info`. Si `G:\Mon Drive\STUDIO VIDÉO` n'est pas connecté, `device_request_folder_access` sur ce dossier (une seule demande). Sans ordinateur relié : utiliser les rushes joints à la discussion, sinon dire comment relier l'app.
2. L'index vit dans le dossier de rushes : `<dossier>\_studio\index.json`. S'il existe, le rapatrier (`device_stage_files`).
3. `device_list_dir` récursif sur le dossier → enregistrer le résultat en `listing.json` → `python3 engine/sync.py <index> listing.json` → rapatrier seulement `to_index` (50 fichiers et 500 Mo maximum par appel : découper).

## 2. Indexer (incrémental)

1. `python3 engine/index_rushes.py <dossier rapatrié> --index <index> --lang <langue des rushes>` : rea-video (coupes, cadrage, caméra, texte incrusté, origine) + Whisper (mots horodatés). Seuls les nouveaux fichiers sont analysés.
2. Regarder chaque planche des nouveaux fichiers (`_studio/sheets/*.jpg`) et écrire les descriptions : `engine/annotate.py <index> apply annotations.json` (description, cadrage, tags, personnes P1…, produits, `usable`). Ne jamais décrire un segment sans avoir vu sa planche.
3. Renvoyer l'index sur l'ordinateur (`device_commit_files` vers `<dossier>\_studio\index.json`) : la prochaine fois, rien ne sera réanalysé.

## 3. Lire le script

Lire le Google Doc (`read_file_content`). Répartir le script dans les cases de la composition (`slots`, avec leur `brief`, leur durée et leur type de voix). Ce qui est dit par une personne filmée → case « speaker » ; ce qui est lu → voix off.

## 4. Écrire le plan de montage

Format : `docs/plan.md`. Règles de choix des segments :
- Témoignage : segments avec visage, net (q ≥ 4), même personne d'une phrase à l'autre si possible ; couper sur les pauses (`annotate.py <index> words F00X`).
- Démo : un plan par idée, 1 à 2 s, étiquette courte (`"Titre|Texte"`).
- Éviter les segments `texte incrusté`, `inutilisable` ou déjà utilisés dans une vidéo récente (`used_in`).
- Voix off en anglais : Kokoro (gratuit). Autre langue ou meilleure voix : générer avec Magnific `audio_tts` après `simulate_cost`, sans dépasser le plafond de crédits (`credit_cap`), et passer le fichier dans la ligne (`"audio"`).
- Musique : fichier de `BIBLIOTHÈQUE\SONS` si demandé, sinon `"auto"`.

Puis `engine/sync.py <index> listing.json --need plan.json` et rapatrier les rushes du plan qui ne sont pas déjà là.

## 5. Monter et contrôler

1. `python3 engine/build.py plan.json --preview` ; corriger le plan tant que le moteur signale une erreur (il dit quoi changer).
2. Regarder la planche de l'aperçu ; corriger cadrage, rythme ou choix de plans si besoin.
3. `python3 engine/build.py plan.json` puis `python3 engine/check.py <vidéo>` ; regarder la planche ; ne livrer que si le contrôle est OK.

## 6. Livrer

1. Copier la vidéo et son rapport dans `/mnt/user-data/outputs/`, l'envoyer (`SendUserFile`) et l'écrire dans `G:\Mon Drive\STUDIO VIDÉO\SORTIES\` (`device_commit_files`).
2. Réponse courte : durée, style et composition (avec version), la liste « case → plan utilisé », les avertissements. Pas de récit des étapes.
3. Après accord de l'utilisateur seulement : les sons et plans générés pour cette vidéo rejoignent `BIBLIOTHÈQUE`.

## Mode Atelier (provisoire, retiré une fois la bibliothèque configurée)

Déclencheurs : « nouveau style », « nouvelle composition », « modifie le style X », « valide X », « liste des styles ».

- **Liste** : lire `library/styles`, `library/compositions` (nom, version, statut) et les défauts.
- **Nouveau** : l'utilisateur donne une vidéo de référence. `/tmp/rea-video/.venv/bin/rea-video decompose <ref> -o <dossier> --lang en` (analyse complète : textes, sous-titres, sons, rythme). Lire `VIDEO.md`, `video/packaging.md`, `video/sound.md`, regarder `storyboard.jpg` ; vérifier soi-même ce que rea-video estime (filmé ou généré). Écrire `library/styles/<id>.json` ou `library/compositions/<id>.json` (`version: 1`, `status: brouillon`), habillé avec la marque, sur le modèle des fiches existantes. Si le style demande un rendu que `render/src/Edit.jsx` ne sait pas faire, l'ajouter au modèle.
- **Modifier** : changer les champs demandés, `version + 1`, statut brouillon ; sortir une vidéo test (rushes et script de `STUDIO VIDÉO\TEST`) ; la repasser dans rea-video et comparer à la référence (durée moyenne des plans, taille et position des sous-titres).
- **Valider** : `status: validé`, puis commit et push sur le dépôt. En production, proposer d'abord les fiches validées ; une fiche en brouillon sert quand l'utilisateur la nomme ou qu'il n'en existe pas d'autre.

Fin de commit : les lignes d'attribution demandées par la session.
