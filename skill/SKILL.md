---
name: studio-video
description: Studio Vidéo, deux commandes. Montage = faire une vidéo guidée pas à pas (rushes Drive, script, style et composition choisis dans la bibliothèque, aperçu puis validation). Production = atelier pour créer ou modifier un style ou une composition à partir de références, avec tests et validation.
---

# Studio Vidéo

Deux commandes. Reconnaître celle que l'utilisateur veut ; s'il dit seulement « studio vidéo »,
lui proposer les deux (AskUserQuestion : **Montage** — faire une vidéo ; **Production** — créer ou
modifier un style ou une composition).

| Commande | Déclencheurs | Ce qu'elle fait |
|---|---|---|
| **Montage** | « montage », « fais une vidéo », « monte… » | Guide pas à pas : rushes → script → style → composition → aperçu → validation → livraison |
| **Production** | « production », « atelier », « nouveau style », « nouvelle composition », « modifie le style X » | Crée ou modifie un style, une composition ou les deux à partir de références, avec test et validation |

Règles communes :
- **Une seule question à la fois**, numérotée (« Étape 2/4 »), courte, avec un exemple de réponse.
  Pour un choix dans une liste : AskUserQuestion si 4 options ou moins, sinon liste numérotée dans
  le message (« réponds par le numéro »).
- Ne jamais écrire dans `SORTIES` ni dans la bibliothèque sans la validation explicite de
  l'utilisateur (« valide », « ok », « c'est bon »). Toute autre réponse = modifications demandées.
- Le code et la bibliothèque vivent dans le dépôt `contact190/studio-video` ; les rushes et les vidéos
  finies dans `STUDIO VIDÉO` sur le Drive de l'utilisateur, lu depuis son ordinateur
  (`G:\Mon Drive\STUDIO VIDÉO` via Google Drive pour ordinateur et le pont de l'app Claude). Le
  connecteur Drive ne télécharge pas au-delà de 10 Mo : jamais pour des vidéos, seulement pour le script.

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

## Démarrage technique (chaque session, en silence)

1. `add_repo` contact190/studio-video (accès push), puis `git clone --depth 1` dans `/home/claude/studio-video`.
2. En arrière-plan : `bash setup.sh --voice --rea` (modèles dans `/tmp/studio-models`, rea-video dans
   `/tmp/rea-video`). Poser les premières questions pendant l'installation.

---

## MONTAGE (faire une vidéo)

Poser les quatre questions dans cet ordre, une par message, puis travailler sans autre question.

**Étape 1/4 — Les rushes.** « Envoie le lien du dossier Drive de tes rushes (ou réponds
*VideoAsk* pour utiliser `BIBLIOTHÈQUE/RUSHES`). »
→ Retrouver le dossier sur l'ordinateur : nom du dossier via le connecteur Drive (ID du lien), puis
chemin sous `G:\Mon Drive` (`device_list_dir`). Hors de `STUDIO VIDÉO` : `device_request_folder_access`
une seule fois. Lancer tout de suite le rapatriement et l'indexation (section *Moteur*, 1–2) pendant
les questions suivantes.

**Étape 2/4 — Le script.** « Envoie ton script : lien Google Doc, fichier, ou colle le texte. »

**Étape 3/4 — Le style.** `python3 engine/library.py styles` → afficher la liste numérotée
(nom, version, statut, description, défaut marqué). « Choisis un style (numéro), ou *défaut*. »

**Étape 4/4 — La composition.** `python3 engine/library.py compositions` → même présentation.
Format : 9:16 sauf si l'utilisateur en a demandé un autre (ne pas poser la question).

Puis annoncer en une ligne : « Je monte : <style> + <composition>, 9:16. Je reviens avec un aperçu. »

**Aperçu.** Moteur 3–5 en mode aperçu ; envoyer l'aperçu (`SendUserFile`) avec la liste
« case → plan utilisé » et demander : « **C'est validé, ou tu veux des modifications ?** »
- Modifications : appliquer (changer un plan, couper, rythme, textes, musique), refaire un aperçu,
  redemander. Recommencer jusqu'à validation.
- Validé : rendu final + contrôle (`check.py`), puis livraison (Moteur 6).

---

## PRODUCTION (atelier : créer ou modifier un style, une composition ou les deux)

**Étape 1 — Ce qu'on fait.** Si ce n'est pas déjà dit : AskUserQuestion « Tu veux créer ou modifier
quoi ? » → *Un style* · *Une composition* · *Les deux*. Pour une modification : `engine/library.py`
et demander laquelle.

**Étape 2 — Les références.** « Envoie une ou plusieurs vidéos de référence, ou le lien d'un dossier
Drive de références. » (Une modification peut se faire sans référence : demander ce qu'il faut changer.)

**Étape 3 — Analyse.** Rapatrier les références (gros fichiers : pont de l'ordinateur). Pour chacune :
`/tmp/rea-video/.venv/bin/rea-video decompose <ref> -o <dossier> --lang <langue>` (analyse complète :
plans, textes, sous-titres, sons, rythme). Lire `VIDEO.md`, `video/packaging.md`, `video/sound.md`,
regarder `storyboard.jpg` ; vérifier soi-même ce que rea-video estime (filmé ou généré). Avec plusieurs
références : garder ce qui est commun (durée moyenne des plans, taille et position des sous-titres,
ordre des parties, durée totale) et signaler ce qui varie.

**Étape 4 — Proposition.** Écrire la fiche (`library/styles/<id>.json` et/ou
`library/compositions/<id>.json`, `version: 1` ou `version + 1`, `status: brouillon`) sur le modèle des
fiches existantes, avec un champ `description` d'une ligne. Si le style demande un rendu que
`render/src/Edit.jsx` ne sait pas faire, l'ajouter au modèle. Résumer la fiche en mots simples
(5 lignes maximum), sans JSON.

**Étape 5 — Test.** Monter une vidéo test avec les rushes et le script de `STUDIO VIDÉO/TEST`
(Moteur 3–5) ; la repasser dans rea-video et comparer à la référence. Envoyer la vidéo test et
demander : « **C'est validé, ou tu veux des modifications ?** »
- Modifications : changer la fiche (`version + 1`), refaire un test, redemander. À chaque nouveau test,
  redemander.
- Validé : `status: validé`, `description` à jour, commit et push. La fiche apparaît dans les listes
  du Montage (les fiches validées en premier). Réponse : nom, version, ce qui a été validé.

---

## MOTEUR (étapes techniques, communes aux deux commandes)

**1. Rapatrier les rushes.** `get_device_info` ; dossier non connecté → `device_request_folder_access`
(une seule demande). L'index vit dans `<dossier>/_studio/index.json` : s'il existe, le rapatrier.
`device_list_dir` récursif → `listing.json` → `python3 engine/sync.py <index> listing.json` → rapatrier
seulement `to_index` (50 fichiers et 500 Mo maximum par appel : découper). Sans ordinateur relié :
utiliser les rushes joints à la discussion, sinon dire comment relier l'app.

**2. Indexer (incrémental).** `python3 engine/index_rushes.py <dossier> --index <index> --lang <langue>`
(rea-video + Whisper ; seuls les nouveaux fichiers sont analysés). Regarder chaque planche des nouveaux
fichiers (`_studio/sheets/*.jpg`) et écrire les descriptions (`engine/annotate.py <index> apply
annotations.json`). Ne jamais décrire un segment sans avoir vu sa planche. Renvoyer l'index sur
l'ordinateur (`device_commit_files`).

**3. Script → cases.** Lire le script (`read_file_content` pour un Google Doc). Répartir dans les cases
de la composition (`slots` : `brief`, durée, type de voix). Dit par une personne filmée → « speaker » ;
lu → voix off.

**4. Plan de montage** (`docs/plan.md`) :
- Témoignage : visage, net (q ≥ 4), même personne si possible ; couper sur les pauses
  (`annotate.py <index> words F00X`).
- Démo : un plan par idée, 1 à 2 s, étiquette courte (`"Titre|Texte"`).
- Éviter `texte incrusté`, `inutilisable`, ou déjà utilisé récemment (`used_in`).
- Voix off anglaise : Kokoro (gratuit). Autre langue ou meilleure voix : Magnific `audio_tts` après
  `simulate_cost`, sans dépasser `credit_cap`.
- Musique : `BIBLIOTHÈQUE/SONS` si demandé, sinon `"auto"`.
Puis `engine/sync.py <index> listing.json --need plan.json` et rapatrier ce qui manque.

**5. Monter et contrôler.** `python3 engine/build.py plan.json --preview` (corriger tant que le moteur
signale une erreur ; regarder la planche). Après validation : `python3 engine/build.py plan.json`,
`python3 engine/check.py <vidéo>`, regarder la planche, ne livrer que si le contrôle est OK.

**6. Livrer (seulement après validation).** Copier la vidéo et son rapport dans
`/mnt/user-data/outputs/`, l'envoyer (`SendUserFile`) et l'écrire dans `STUDIO VIDÉO/SORTIES/`
(`device_commit_files`). Réponse courte : durée, style et composition (avec version), « case → plan »,
avertissements. Les sons et plans générés rejoignent `BIBLIOTHÈQUE` seulement si l'utilisateur le dit.

Fin de commit : les lignes d'attribution demandées par la session.
