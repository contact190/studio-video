#!/usr/bin/env python3
"""Retrouver ce qui passe entre deux secondes d'une vidéo montée (pour appliquer une note).

Usage : python3 engine/locate.py <rapport .report.json> <début s> <fin s>
Affiche la case, le segment, le fichier d'origine et ses points d'entrée/sortie.
"""
import json
import sys


def main():
    rep, t0, t1 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    r = json.load(open(rep, encoding='utf-8'))
    edit = r['edit']
    hits = []
    for i, e in enumerate(edit):
        end = edit[i + 1]['at'] if i + 1 < len(edit) else r.get('duration', e['at'] + 99)
        if e['at'] < t1 and end > t0:
            hits.append(e | {'until': round(end, 2)})
    if not hits:
        print('Rien entre ces secondes (carton final ou hors durée).')
    for h in hits:
        print(f"{h['at']:>6.2f}–{h['until']:<6.2f} case {h['slot']:<14} {h['segment']:<10} "
              f"{h.get('file', '')} [{h.get('in', '')}→{h.get('out', '')}] {h.get('description', '')}")


if __name__ == '__main__':
    main()
