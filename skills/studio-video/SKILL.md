---
name: studio-video
description: Studio Vidéo, quatre commandes. Analyse = indexer une fois des dossiers de rushes. Montage = à partir d'un brief et des rushes, produire 10 à 20 variantes (styles et compositions de la bibliothèque, voix off anglaise, validation une par une). Production = créer ou modifier un style ou une composition. Gagnants = classer les pubs Meta d'une période et décliner les meilleures en variantes.
---

# Studio Vidéo

Quatre commandes. Reconnaître celle que l'utilisateur veut ; s'il dit seulement « studio vidéo »,
lui proposer les quatre (AskUserQuestion).

| Commande | Déclencheurs | Ce qu'elle fait |
|---|---|---|
| **Analyse** | « analyse », « indexe ce dossier » | Analyse un ou plusieurs dossiers une seule fois, range les vidéos dans `RUSHES`, met l'index et le sheet à jour |
| **Montage** | « montage », « fais des variantes », « fais une vidéo » | Brief + rushes → 10, 15 ou 20 variantes, planche de choix, aperçus, validation une par une |
| **Production** | « production », « atelier », « nouveau style » | Crée ou modifie un style, une composition ou les deux, avec test et validation |
| **Gagnants** | « gagnants », « meilleures pubs », « analyse Meta » | Classe les pubs Meta d'une période, analyse celles choisies (composition, style, script) et les décline en variantes jusqu'au résultat final |

Règles communes :
- **Une seule question à la fois**, numérotée, courte, avec un exemple de réponse. Choix dans une
  liste : AskUserQuestion si 4 options ou moins, sinon liste numérotée (« réponds par le numéro »).
- Rien n'est écrit dans `SORTIES` ni dans la bibliothèque sans validation explicite.
- Les rushes, l'index et les vidéos finies sont dans `STUDIO VIDÉO` sur le Drive de l'utilisateur,
  lu depuis son ordinateur (Google Drive pour ordinateur, via le pont de l'app Claude). Le lecteur
  dépend du compte (`G:\Mon Drive`, `H:\Mon Drive`…) : le retrouver avec `get_device_info` /
  `device_list_dir` et le noter dans `Réglages`. Le connecteur Drive ne télécharge pas au-delà de
  10 Mo : jamais pour des vidéos, seulement pour le brief, le script et le sheet.
- **Une vidéo n'est analysée qu'une fois.** L'index (`RUSHES/_studio/index.json`) garde chaque fichier
  (reconnu par nom, taille et date) avec ses segments, sa transcription mot à mot, sa qualité, ses
  personnes, produits et usages. Il est recopié dans le sheet PILOTAGE (onglets `Rushes` et
  `Segments`) pour être lisible. Montage ne réanalyse jamais un fichier déjà indexé.

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
   `STUDIO VIDÉO/SORTIES`, `STUDIO VIDÉO/TEST`, et le sheet `PILOTAGE` (onglets `Réglages`, `Rushes`, `Segments`) dans `STUDIO VIDÉO`, toujours dans le compte de l'utilisateur. Noter l'ID de `RUSHES` et du sheet.
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
2. En arrière-plan : `bash setup.sh --voice --rea` (Whisper, voix off anglaise Kokoro open source,
   rea-video). Poser les premières questions pendant l'installation.

## À l'ouverture : nouvelles vidéos

Avant la première question : rapatrier l'index de `RUSHES`, lister `RUSHES` (`device_list_dir`
récursif → `listing.json`) et lancer `python3 engine/sync.py <index> listing.json`. S'il y a des
fichiers dans `to_index`, le dire en une ligne et proposer (AskUserQuestion) : *Les analyser et faire
des variantes* (→ Analyse sur ces fichiers, puis Montage avec ces vidéos imposées) · *Les analyser
seulement* · *Plus tard*. Sinon, ne rien dire.

---

## ANALYSE (indexer une fois)

1. « Envoie le ou les dossiers à analyser (liens Drive ou chemins). »
2. Pour chaque dossier hors de `RUSHES` : demander une fois pour tous « Je les range dans `RUSHES`
   (recommandé : ils serviront à tous les montages) ou je les analyse sur place ? ». Ranger = copier
   les fichiers dans `RUSHES/<nom du dossier>/` (connecteur Drive `copy_file`, même compte) avant
   l'analyse.
3. Moteur 1–2 : seuls les fichiers absents de l'index sont rapatriés et analysés.
4. Sheet : `python3 engine/index_export.py <index> --out /tmp` puis écrire `rushes.json` et
   `segments.json` dans les onglets `Rushes` et `Segments` du sheet PILOTAGE (Google Sheets
   `update_values`, à partir de A1, après avoir vidé l'onglet). Pas de sheet : le créer dans
   `STUDIO VIDÉO` du compte de l'utilisateur.
5. Réponse : nombre de vidéos ajoutées, durée totale, personnes et produits repérés, segments
   inutilisables et pourquoi.

---

## MONTAGE (variantes à partir d'un brief)

Questions, une par message :

1. **Le brief.** « Envoie ton brief (lien Google Doc, fichier ou texte). » Modèle à proposer si
   l'utilisateur n'en a pas : rubriques ci-dessous. Le lire et le résumer en `brief.json`
   (`subject`, `goal`, `audience`, `messages`, `hooks`, `proofs`, `tone`, `cta`, `end_text`,
   `bullets`, `avoid`, `language`, `duration`, `questions`, `reviews`). Une rubrique obligatoire manque → la demander.
2. **Les rushes.** « Les rushes : `RUSHES` (déjà indexés), ou le lien d'un autre dossier ? » Autre
   dossier → « Je l'indexe et le range dans `RUSHES`, ou je travaille directement avec ? » puis
   Analyse sur ce dossier (seulement les nouveaux fichiers).
3. **Vidéos imposées** (facultatif). « Des vidéos à utiliser obligatoirement dans toutes les
   variantes ? (noms ou liens, ou *non*) » → identifiants `F00X` ou `F00X.S0Y`.
4. **Références** (facultatif). « Des vidéos ou liens de référence pour l'esprit ? (ou *non*) » →
   les regarder (rea-video si vidéo) et en tirer le ton, le rythme, les accroches.
5. **Style et composition.** AskUserQuestion : *Auto* (le skill répartit sur la bibliothèque) ·
   *Choisir*. Choisir → listes numérotées `engine/library.py styles` puis `compositions` : recopier
   chaque choix avec sa ligne **ⓘ** (quand le choisir, idéal pour), et ajouter « Pour le détail
   d'un choix, réponds *i* + le numéro ». *i 7* → `engine/library.py info <id>` (à quoi ça ressemble,
   quand le choisir, idéal pour, ce qu'il faut dans les rushes), puis reposer la question. Plusieurs
   numéros possibles (« 2, 5, 9 ») : les variantes se répartissent entre eux.
6. **Nombre de variantes.** AskUserQuestion : *10* · *15* · *20*.
7. **Nom des vidéos.** « Pour le nom final : la date (MM.JJ.AA, aujourd'hui par défaut), le numéro
   produit (ex. 001) et l'identifiant (ex. ryad) ? » Le nom sera
   `MM.JJ.AA_<produit>_<identifiant>_Videoask_V<x>` (ex. `11.10.26_001_ryad_Videoask_V4`) ; `V<x>` est
   calculé seul : dernière version de ce préfixe trouvée dans `SORTIES`, plus 1. Ne pas le demander.

Puis, sans autre question :

1. `python3 engine/variants.py matrix <index> --n N --style <auto|id> --composition <auto|id>
   --must <F003,…> --project <nom>` : répartit les variantes (compositions possibles avec ces rushes
   seulement, personne principale qui a assez de parole, accroches tournantes).
2. `python3 engine/variants.py draft variants.json brief.json --out plans` : premier jet de chaque
   plan. **Relire chaque plan** : réécrire l'accroche et les lignes de voix off depuis le brief (ton,
   messages, `avoid`), vérifier sur les planches que chaque plan montre ce que dit la ligne, couper sur
   les pauses (`annotate.py <index> words F00X`). Voix off : anglais seulement, Kokoro ; un mot
   inconnu de la voix → l'ajouter à `tts/lexicon-extra.txt` (phonèmes sur le modèle des mots voisins).
3. **Planche.** `python3 engine/variants.py board variants.json --plans plans` → envoyer le tableau
   (variante, style, composition, personne, accroche, durée) et demander : « Lesquelles je monte ?
   (*toutes*, ou les numéros) ».
4. **Aperçus.** `python3 engine/variants.py build plans --only V01,V04,…` (≈ 3 à 4 min par vidéo :
   prévenir de la durée). Envoyer les aperçus au fur et à mesure (`SendUserFile`).
5. **Validation une par une.** Pour chaque variante, dans l'ordre, demander :
   « **V03** — validée, ou une note ? Format : `V03 4–7 s : <ce qu'il faut changer>` (plusieurs
   lignes possibles) ». Pour une note : `python3 engine/locate.py <rapport V03> 4 7` → la case et le
   plan concernés ; modifier le plan, refaire l'aperçu de cette seule variante, redemander.
   « validée » → variante suivante.
6. **Livraison** des variantes validées : `variants.py build plans --final --only …`, `check.py`
   sur chacune. Lister `SORTIES` (`device_list_dir` → `sorties.json`), puis
   `variants.py names variants.json --date … --product … --ident … --existing sorties.json --only <validées>`
   et livrer chaque vidéo sous son `final_name` (Moteur 6), dans l'ordre de validation. Pendant le
   travail, les variantes gardent leur nom de travail (`<projet>_V03_<style>_<composition>`).

### Le brief (modèle)

| Rubrique | Obligatoire | Exemple |
|---|---|---|
| Sujet | oui | Les clients adorent la douceur du t-shirt chanvre |
| Objectif | oui | Acheter |
| Public | oui | Hommes 25–45, déjà clients |
| Messages clés (2 à 4, par importance) | non | Doux · respirant · garde sa forme |
| Accroches possibles | non | « Finally, a shirt that fits » |
| Preuves | non | Test d'arrachage, 51 % chanvre, garantie |
| Ton | non | Authentique |
| Appel à l'action + texte de fin | non | Shop now · Built to last |
| À éviter | non | Pas de prix, pas de concurrent nommé |
| Langue et durée | non | Anglais, 20 à 40 s |
| Questions posées (VideoAsk) | non | Does it really fit? · How does it feel? (affichées en carton dans *Réponse à une question*) |
| Avis écrits | non | « Softest tee I own » (cartes d'avis du style *Avis clients*) |

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

## GAGNANTS (pubs Meta → variantes)

Questions, une par message :

1. **Connexion Meta.** Chercher les outils Meta (`ToolSearch` « +Meta ads »). Absents ou non
   connectés → `SearchMcpRegistry` [« meta ads »] puis `SuggestConnectors` (connecteur **Meta**) et
   attendre « c'est connecté ». Ne jamais passer à la suite sans connexion.
2. **Compte publicitaire.** `ads_get_ad_accounts`. Un seul → le dire et continuer. Plusieurs →
   AskUserQuestion (nom et numéro). Compte sans aucune pub → le dire et proposer un autre compte ou
   la Bibliothèque publicitaire (`ads_library_search` : pubs publiques d'une marque, sans chiffres ;
   une pub active depuis longtemps est en général une gagnante).
3. **Période.** « Du … au … ? (ex. 01.10.26 au 15.11.26, ou *30 derniers jours*) » → `time_range`
   ou `date_preset`.

Puis :

4. **Classement.** Vérifier les champs (`ads_get_field_context`), puis `ads_get_ad_entities` level=ad,
   période choisie, champs : `id, name, campaign_name, effective_status, creative_id, amount_spent,
   impressions, ctr, results, cost_per_result, video_play_actions,
   video_continuous_2_sec_watched_actions, video_thruplay_watched_actions,
   video_p75_watched_actions, video_avg_time_watched_actions` (suivre `next_cursor` jusqu'au bout ;
   exécuter les `next_actions` en lecture seule). Enregistrer en `ads.json`, puis
   `python3 engine/meta_rank.py ads.json --out rank.json`. Envoyer le tableau (rang, pub, dépense,
   résultats, coût par résultat, accroche, rétention, CTR, score, recommandation) avec 2 ou 3 lignes
   de lecture en mots simples, puis demander : « Lesquelles je décline ? (numéros) ». Recommander
   les « Gagnante ». Ne jamais modifier les campagnes (lecture seule).
5. **Récupérer les vidéos choisies.** `ads_get_creatives` (creative_ids) → `video_id`, texte de la
   pub (`body`, `title`) ; `ads_get_ad_videos` (video_ids, fields `download_hd_url`). L'espace de
   travail ne joint pas les serveurs vidéo de Meta : télécharger sur l'ordinateur de l'utilisateur
   (`device_bash` : `curl -L -o "<STUDIO VIDÉO>/BIBLIOTHÈQUE/RÉFÉRENCES/META/<ad_id>.mp4" "<url>"`),
   puis rapatrier (`device_stage_files`). Sans ordinateur relié : demander d'autoriser `*.fbcdn.net`
   dans Settings › Capabilities, ou de télécharger la vidéo depuis le Gestionnaire de publicités.
6. **Analyse de chaque gagnante** (comme Production étape 3, `rea-video decompose`) : accroche, script
   mot à mot, parties et durées, rythme, sous-titres, textes à l'écran, musique. Résumer en 5 lignes
   avec les chiffres Meta.
7. **Composition et style.** Comparer à la bibliothèque (`engine/library.py all --json`). Déjà
   présents → le dire et les utiliser. Absents → créer la fiche (Production étape 4) avec
   `source: "meta:<ad_id>"`, `status: brouillon` et dans `info` les chiffres Meta (accroche, rétention,
   coût par résultat, période) ; la montrer et demander validation (test monté comme Production
   étape 5 si l'utilisateur le veut). Validé → `status: validé`, commit et push.
8. **Nombre de variantes par vidéo.** AskUserQuestion : *5* · *10* · *15* · *20*.
9. **Scripts.** Écrire `brief.json` depuis la gagnante (sujet, messages dans son ordre, accroche
   d'origine en tête de `hooks`, texte de la pub, CTA) et proposer les angles : nouvelles accroches,
   autre personne, autre ordre, autre durée — **une seule chose changée par variante**, pour savoir
   au prochain test ce qui a fait la différence. Montrer la liste des scripts et demander validation.
10. **Rushes.** Indexer la gagnante dans `RUSHES/META` (Analyse) pour réutiliser ses plans, plus les
    rushes existants.
11. **Suite = MONTAGE à partir de « Puis, sans autre question »** (matrix avec la composition et le
    style de la gagnante, draft, planche, aperçus, validation une par une, nom final — demander date,
    numéro produit et identifiant si pas encore donnés). Les variantes gardent dans leur rapport
    `source_ad: <ad_id>`.

---

## MOTEUR (étapes techniques, communes aux commandes)

**1. Rapatrier les rushes.** `get_device_info` ; dossier non connecté → `device_request_folder_access`
(une seule demande). L'index vit dans `<dossier>/_studio/index.json` : s'il existe, le rapatrier.
`device_list_dir` récursif → `listing.json` → `python3 engine/sync.py <index> listing.json` → rapatrier
seulement `to_index` (50 fichiers et 500 Mo maximum par appel : découper). Sans ordinateur relié :
utiliser les rushes joints à la discussion, sinon dire comment relier l'app.

**2. Indexer (incrémental).** `python3 engine/index_rushes.py <dossier> --index <index> --lang <langue>`
(rea-video + Whisper ; seuls les nouveaux fichiers sont analysés ; les mots sont ensuite recalés sur les vrais silences par `engine/realign.py`, lancé automatiquement — à lancer à la main sur un ancien index). Règle de coupe : un plan parlé commence au début d'une phrase et finit à la fin d'une phrase, jamais au milieu (le premier jet de `variants.py draft` l'applique déjà ; la garder en relisant les plans). Regarder chaque planche des nouveaux
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
