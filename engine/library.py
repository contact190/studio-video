#!/usr/bin/env python3
"""Liste la bibliothèque pour les choix guidés du skill.

Usage :
  python3 engine/library.py styles          → liste numérotée des styles
  python3 engine/library.py compositions    → liste numérotée des compositions
  python3 engine/library.py all --json      → tout, en JSON
  python3 engine/library.py fins            → mises en page de fin (CTA), avec ⓘ
  python3 engine/library.py info <id>       → fiche (i) : à quoi ça ressemble, quand l'utiliser, ce qu'il faut
Ordre : validés d'abord, puis brouillons ; le défaut est marqué.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / 'library'


def describe(kind, d):
    if kind == 'compositions':
        slots = d.get('slots', [])
        parts = ' › '.join(s.get('id', s.get('name', '?')) for s in slots)
        dur = d.get('target_duration')
        if isinstance(dur, (list, tuple)) and len(dur) == 2:
            parts += f'  ({dur[0]}–{dur[1]} s)'
        return d.get('description') or parts
    sub = d.get('subtitles', {})
    bits = []
    if sub:
        bits.append(f"sous-titres {sub.get('max_words', '?')} mots, {sub.get('font', 'Inter')}")
    if d.get('end_card'):
        bits.append('carte de fin')
    return d.get('description') or ', '.join(bits)


def items(kind):
    defaults = json.loads((LIB / 'defaults.json').read_text(encoding='utf-8'))
    default_id = defaults.get('style' if kind == 'styles' else 'composition')
    out = []
    for p in sorted((LIB / kind).glob('*.json')):
        d = json.loads(p.read_text(encoding='utf-8'))
        out.append({
            'id': d.get('id', p.stem), 'name': d.get('name', p.stem),
            'version': d.get('version', 1), 'status': d.get('status', 'brouillon'),
            'default': d.get('id', p.stem) == default_id, 'description': describe(kind, d), 'info': d.get('info', {}),
        })
    out.sort(key=lambda x: (x['status'] != 'validé', not x['default'], x['name']))
    return out


LABELS = [('quoi', 'À quoi ça ressemble'), ('quand', 'Quand le choisir'), ('ideal_pour', 'Idéal pour'), ('besoin', 'Ce qu\'il faut dans les rushes')]


def show_info(ident):
    for k in ('styles', 'compositions'):
        for it in items(k):
            if it['id'] == ident or it['name'].lower() == ident.lower():
                print(f"ⓘ {it['name']} ({'style' if k == 'styles' else 'composition'}, v{it['version']}, {it['status']})")
                for key, lab in LABELS:
                    if it['info'].get(key):
                        print(f"  {lab} : {it['info'][key]}")
                return
    sys.exit(f'inconnu : {ident}')


def show_ends():
    d = json.loads((Path(__file__).resolve().parent.parent / 'library' / 'ctas.json').read_text(encoding='utf-8'))
    for i, l in enumerate(d['layouts'], 1):
        print(f"{i}. {l['name']} — {l['description']}")
        print(f"   ⓘ {l['info']['quand']} Idéal pour : {l['info']['ideal_pour']}")


def main():
    if sys.argv[1:2] == ['fins']:
        show_ends()
        return
    if sys.argv[1:2] == ['info']:
        show_info(' '.join(sys.argv[2:]))
        return
    kinds = ['styles', 'compositions'] if sys.argv[1:2] == ['all'] else sys.argv[1:2] or ['styles']
    if '--json' in sys.argv:
        print(json.dumps({k: items(k) for k in kinds}, ensure_ascii=False, indent=1))
        return
    for k in kinds:
        print(k.upper())
        for i, it in enumerate(items(k), 1):
            mark = ' (par défaut)' if it['default'] else ''
            print(f"{i}. {it['name']}{mark} — {it['description']}")
            if it['info'].get('quand'):
                print(f"   ⓘ {it['info']['quand']} Idéal pour : {it['info'].get('ideal_pour', '—')}")


if __name__ == '__main__':
    main()
