#!/usr/bin/env python3
"""Exporter l'index en lignes pour le sheet PILOTAGE (onglets Rushes et Segments).

Usage : python3 engine/index_export.py <index.json> [--out dossier]
Écrit rushes.json et segments.json : listes de lignes (en-tête compris) prêtes pour
l'outil Google Sheets (update_values, saisie brute). La transcription complète va dans
Segments ; un fichier déjà présent garde son identifiant (F001…).
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('index')
    ap.add_argument('--out', default='.')
    a = ap.parse_args()
    idx = json.load(open(a.index, encoding='utf-8'))
    rushes = [['ID', 'Fichier', 'Chemin', 'Durée (s)', 'Format', 'Parole', 'Segments', 'Résumé']]
    for fid, f in sorted(idx['files'].items()):
        rushes.append([fid, f.get('name', ''), f.get('rel', f.get('path', '')), round(f.get('duration', 0), 2),
                       f"{f.get('width', '')}x{f.get('height', '')}", 'oui' if f.get('has_audio') else 'non',
                       f.get('n_segments', 0), f.get('summary', '')])
    segs = [['ID', 'Fichier', 'Début', 'Fin', 'Durée', 'Qualité', 'Utilisable', 'Problèmes', 'Personnes',
             'Produits', 'Tags', 'Cadrage', 'Description', 'Transcription', 'Utilisé dans']]
    for sid, s in sorted(idx['segments'].items()):
        segs.append([sid, idx['files'].get(s['file'], {}).get('name', s['file']), s['start'], s['end'],
                     round(s.get('dur', 0), 2), s.get('quality', ''), 'oui' if s.get('usable', True) else 'non',
                     ', '.join(s.get('issues', [])), ', '.join(s.get('people', [])), ', '.join(s.get('products', [])),
                     ', '.join(s.get('tags', [])), s.get('framing', ''), s.get('description', ''),
                     s.get('transcript', ''), ', '.join(s.get('used_in', []))])
    out = Path(a.out)
    (out / 'rushes.json').write_text(json.dumps(rushes, ensure_ascii=False), encoding='utf-8')
    (out / 'segments.json').write_text(json.dumps(segs, ensure_ascii=False), encoding='utf-8')
    print(f'{len(rushes) - 1} rushes, {len(segs) - 1} segments → {out}/rushes.json, segments.json')


if __name__ == '__main__':
    main()
