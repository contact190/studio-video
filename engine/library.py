#!/usr/bin/env python3
"""Liste la bibliothèque pour les choix guidés du skill.

Usage :
  python3 engine/library.py styles          → liste numérotée des styles
  python3 engine/library.py compositions    → liste numérotée des compositions
  python3 engine/library.py all --json      → tout, en JSON
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
            'default': d.get('id', p.stem) == default_id, 'description': describe(kind, d),
        })
    out.sort(key=lambda x: (x['status'] != 'validé', not x['default'], x['name']))
    return out


def main():
    kinds = ['styles', 'compositions'] if sys.argv[1:2] == ['all'] else sys.argv[1:2] or ['styles']
    if '--json' in sys.argv:
        print(json.dumps({k: items(k) for k in kinds}, ensure_ascii=False, indent=1))
        return
    for k in kinds:
        print(k.upper())
        for i, it in enumerate(items(k), 1):
            mark = ' (par défaut)' if it['default'] else ''
            print(f"{i}. {it['name']} — v{it['version']}, {it['status']}{mark} — {it['description']}")


if __name__ == '__main__':
    main()
