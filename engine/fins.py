#!/usr/bin/env python3
"""Fins de vidéo (CTA) : regarder la fin d'une référence, créer ou valider une fin.

  python3 engine/fins.py look ref.mp4 [--last 6] [--out dir]
      → planche des dernières secondes (12 images) + texte entendu, pour s'inspirer du CTA.
  python3 engine/fins.py add --id <id> --name "<nom>" --base <mise en page> --desc "<une ligne>"
        [--style '{"bg":"#000","accent":"#ff2d55","button_shape":"square"}']
        [--cta "Get yours · Shop now"] [--headline "Built to last."] [--source ref|prompt|montage]
        [--quand "…"] [--ideal "…"]
      → ajoute (ou met à jour, version + 1) une fin en brouillon dans library/ctas.json.
  python3 engine/fins.py validate <id>   → statut validé : utilisée par défaut en Auto.
Mises en page de base : classique, bouton, offre, garantie, avis, superpose, question, minimal.
Réglages possibles (style) : bg, glow, accent, headline_color, headline_size, show_logo, show_bullets,
button_shape (pill|square|outline), button_upper (true|false), button_arrow (true|false).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

LIB = Path(__file__).resolve().parent.parent / 'library' / 'ctas.json'
BASES = ['classique', 'bouton', 'offre', 'garantie', 'avis', 'superpose', 'question', 'minimal']
KEYS = {'bg', 'glow', 'accent', 'headline_color', 'headline_size', 'show_logo', 'show_bullets', 'button_shape',
        'button_upper', 'button_arrow', 'cta_text'}


def split(t):
    return [x.strip() for x in str(t or '').split('·') if x.strip()]


def look(a):
    out = Path(a.out or Path(a.ref).with_suffix('').as_posix() + '_fin')
    out.mkdir(parents=True, exist_ok=True)
    d = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', a.ref],
                             capture_output=True, text=True).stdout)
    t0 = max(0.0, d - a.last)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t0:.2f}', '-i', a.ref, '-vf',
                    f'fps={12 / a.last:.3f},scale=240:-2,tile=6x2', '-frames:v', '1', str(out / 'fin_sheet.jpg')], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t0:.2f}', '-i', a.ref, '-ac', '1', '-ar', '16000',
                    str(out / 'fin.wav')], check=True)
    text = ''
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import index_rushes  # noqa: transcription Whisper déjà installée par setup.sh
        text = ' '.join(r['text'] for r in index_rushes.speech_regions(out / 'fin.wav', '', True))
    except Exception:
        pass
    print(json.dumps({'sheet': str(out / 'fin_sheet.jpg'), 'start': round(t0, 2), 'duration': round(d, 2), 'heard': text},
                     ensure_ascii=False))


def add(a):
    d = json.loads(LIB.read_text(encoding='utf-8'))
    if a.base not in BASES:
        sys.exit(f'base inconnue : {a.base} (choix : {", ".join(BASES)})')
    st = json.loads(a.style) if a.style else {}
    bad = set(st) - KEYS
    if bad:
        sys.exit(f'réglages inconnus : {", ".join(sorted(bad))}')
    cur = next((l for l in d['layouts'] if l['id'] == a.id), None)
    entry = {'id': a.id, 'name': a.name, 'base': a.base, 'description': a.desc, 'end_style': st,
             'status': 'brouillon', 'version': (cur['version'] + 1) if cur else 1, 'source': a.source,
             'info': {'quoi': a.desc, 'quand': a.quand or '', 'ideal_pour': a.ideal or ''}}
    if a.cta:
        entry['cta_texts'] = split(a.cta)
    if a.headline:
        entry['headlines'] = split(a.headline)
    if cur:
        d['layouts'][d['layouts'].index(cur)] = entry
    else:
        d['layouts'].append(entry)
    LIB.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"{'mise à jour' if cur else 'ajoutée'} : {a.id} (v{entry['version']}, brouillon)")


def validate(a):
    d = json.loads(LIB.read_text(encoding='utf-8'))
    for l in d['layouts']:
        if l['id'] == a.id:
            l['status'] = 'validé'
            LIB.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
            print(f'{a.id} validée : utilisée par défaut en Auto')
            return
    sys.exit(f'fin inconnue : {a.id}')


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    l = sub.add_parser('look'); l.add_argument('ref'); l.add_argument('--last', type=float, default=6); l.add_argument('--out')
    p = sub.add_parser('add')
    for k in ('id', 'name', 'base', 'desc'):
        p.add_argument(f'--{k}', required=True)
    for k in ('style', 'cta', 'headline', 'quand', 'ideal'):
        p.add_argument(f'--{k}')
    p.add_argument('--source', default='prompt')
    v = sub.add_parser('validate'); v.add_argument('id')
    a = ap.parse_args()
    {'look': look, 'add': add, 'validate': validate}[a.cmd](a)


if __name__ == '__main__':
    main()
