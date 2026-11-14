"""Ajoute les descriptions écrites par Claude (après lecture des planches) dans l'index,
et affiche l'index sous forme lisible.

Usage :
  python3 engine/annotate.py <index.json> apply <annotations.json>
      annotations.json : [{"id": "F001.S03", "description": "...", "framing": "gros plan",
                           "tags": ["atelier"], "people": ["P1"], "products": ["fenetre"],
                           "usable": true}, ...]
      ou {"files": {"F001": {"summary": "..."}}, "segments": [...]}
  python3 engine/annotate.py <index.json> list [--todo] [--file F001]
      --todo : seulement les segments pas encore décrits
  python3 engine/annotate.py <index.json> words F001
      mots horodatés de chaque zone de parole, pour choisir des points d'entrée/sortie précis
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, save_json, fmt_t

FIELDS = {'description', 'framing', 'tags', 'people', 'products', 'usable', 'notes'}


def apply(idx_path, ann_path):
    idx = load_json(idx_path)
    data = load_json(ann_path)
    segs = data if isinstance(data, list) else data.get('segments', [])
    files = {} if isinstance(data, list) else data.get('files', {})
    n, bad = 0, []
    for a in segs:
        s = idx['segments'].get(a.get('id'))
        if not s:
            bad.append(a.get('id')); continue
        for k, v in a.items():
            if k in FIELDS:
                s[k] = v
        n += 1
    for fid, f in files.items():
        if fid in idx['files']:
            idx['files'][fid].update({k: v for k, v in f.items() if k in ('summary', 'people', 'notes')})
    save_json(idx_path, idx)
    print(f'{n} segments mis à jour' + (f' · inconnus : {", ".join(map(str, bad))}' if bad else ''))


def listing(idx_path, todo=False, fid=None):
    idx = load_json(idx_path)
    for f_id, f in sorted(idx['files'].items()):
        if fid and f_id != fid: continue
        print(f"\n## {f_id} {f['name']} · {f['duration']:.1f}s · {f['width']}x{f['height']} · {f.get('summary', '')}")
        for s in sorted((s for s in idx['segments'].values() if s['file'] == f_id), key=lambda s: s['start']):
            if todo and s.get('description'): continue
            flag = '' if s['usable'] else '  [inutilisable]'
            print(f"  {s['id']} {fmt_t(s['start'])}-{fmt_t(s['end'])} ({s['dur']}s) q{s['quality']} {','.join(s['issues'])}{flag}")
            if s.get('description'): print(f"      {s['framing']} · {s['description']} · {s['tags']}")
            if s['transcript']: print(f"      « {s['transcript'][:160]} »")


def words(idx_path, fid):
    idx = load_json(idx_path)
    for sp in idx['files'][fid]['speech']:
        print(f"[{fmt_t(sp['start'])}-{fmt_t(sp['end'])}] " + ' '.join(f"{w}@{t0:.1f}" for w, t0, t1 in sp.get('words', [])))


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    if sys.argv[2] == 'words':
        words(sys.argv[1], sys.argv[3])
    elif sys.argv[2] == 'apply':
        apply(sys.argv[1], sys.argv[3])
    else:
        listing(sys.argv[1], '--todo' in sys.argv, sys.argv[sys.argv.index('--file') + 1] if '--file' in sys.argv else None)
