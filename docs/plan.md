# Le plan de montage

Le plan est un fichier JSON que Claude écrit après avoir lu le script et l'index des rushes.
`engine/build.py` le transforme en vidéo. Rien n'y est deviné : chaque case de la composition
y reçoit ses segments.

```json
{
 "title": "nom-de-la-video",
 "style": "sombre-premium",
 "composition": "temoignage-demo",
 "brand": "neutre",
 "format": "9:16",
 "rushes_index": "/chemin/rushes/_studio/index.json",
 "voice": {"voice": "am_michael", "speed": 1.05},
 "music": "auto",
 "hook_title": "Texte du titre d'accroche",
 "slots": {
  "hook":        {"clips": [{"seg": "F006.S01", "in": 0.0, "out": 3.05}]},
  "testimonial": {"clips": [{"seg": "F004.S01", "in": 2.7, "out": 5.5, "tag": "Real customer|Super soft"}]},
  "demo":        {"audio": "voiceover", "lines": [
                   {"text": "Phrase lue par la voix off.", "clips": [{"seg": "F002.S06", "tag": "Rip test|Passed"}]}
                 ]},
  "end":         {"headline": "Built to last.", "bullets": ["…"], "cta": "Shop now", "image_seg": "F002.S13"}
 }
}
```

## Les deux voix

- **Voix filmée** (`"audio": "speaker"`, par défaut si la composition le prévoit) : la personne
  des rushes parle. `in` et `out` sont des secondes dans le fichier d'origine ; on les choisit
  avec `engine/annotate.py <index> words F004` pour couper sur les pauses. Les sous-titres
  viennent de la transcription ; `"subtitle": "texte corrigé"` la remplace si elle est fausse.
- **Voix off** (`"audio": "voiceover"`) : chaque ligne est lue (Kokoro, anglais) et illustrée par
  ses `clips`, qui se partagent la durée de la phrase. Pour une autre langue ou une meilleure
  voix, générer l'audio ailleurs (Magnific, OpenAI) et le passer avec `"audio": "/chemin.wav"`
  dans la ligne.

## Champs d'un plan (`clip`)

| Champ | Rôle |
|---|---|
| `seg` | Identifiant du segment dans l'index (`F002.S06`) |
| `in`, `out` | Points d'entrée et de sortie (secondes dans le fichier), facultatifs |
| `tag` | Étiquette affichée sur le plan : `"Titre\|Texte"` ou `"Texte"` |
| `focus_x`, `focus_y` | Cadrage quand l'image est recadrée (0 = gauche/haut, 0,5 = centre) |
| `volume` | Son du plan sous une voix off (0 par défaut) |
| `allow_repeat`, `force` | Autoriser un plan déjà utilisé, ou marqué inutilisable |

## Musique

`"music": "auto"` génère une musique de secours par code. `{"file": "/chemin.mp3"}` utilise un
son de la bibliothèque ou un son généré avec Magnific. `"none"` : pas de musique.

## Règles vérifiées avant le rendu

Segment inconnu ou inutilisable, plan déjà utilisé, ligne de voix off plus longue que ses plans,
mot inconnu de la voix off : le montage s'arrête et dit quoi corriger. Durée d'une case ou
durée totale hors des bornes de la composition : simple avertissement.
