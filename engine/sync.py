"""Compare le contenu d'un dossier de rushes (listé sur l'ordinateur via le pont) à l'index,
pour ne rapatrier que ce qui est nécessaire.

Usage :
  python3 engine/sync.py <index.json> <listing.json> [--need plan.json]
     listing.json : la liste renvoyée par device_list_dir (récursif) : [{"name": "a/b.mp4", "size": 123, ...}]
     --need plan.json : ajoute les rushes utilisés par ce plan (à rapatrier pour le montage)
Sortie (JSON) : {"to_index": [...], "known": n, "missing_from_folder": [...], "to_stage": [...]}
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, VIDEO_EXT


def main():
    idx = load_json(sys.argv[1], {'files': {}, 'segments': {}})
    listing = load_json(sys.argv[2], [])
    if isinstance(listing, dict):
        listing = listing.get('entries', [])
    vids = [e for e in listing if e.get('type', 'file') == 'file' and Path(e['name']).suffix.lower() in VIDEO_EXT
            and '_studio' not in Path(e['name']).parts]
    known = {f['key'] for f in idx['files'].values()}
    new = [e['name'] for e in vids if f"{Path(e['name']).name}|{e.get('size')}" not in known]
    present = {f"{Path(e['name']).name}|{e.get('size')}" for e in vids}
    gone = [f.get('rel', f['name']) for f in idx['files'].values() if f['key'] not in present]
    stage = list(new)
    if '--need' in sys.argv:
        plan = load_json(sys.argv[sys.argv.index('--need') + 1])
        fids = set()
        for slot in plan['slots'].values():
            for c in slot.get('clips', []) + [c for l in slot.get('lines', []) for c in l.get('clips', [])]:
                fids.add(c['seg'].split('.')[0])
            if slot.get('image_seg'):
                fids.add(slot['image_seg'].split('.')[0])
        stage += [idx['files'][f].get('rel', idx['files'][f]['name']) for f in sorted(fids) if f in idx['files']]
    print(json.dumps({'to_index': new, 'known': len(vids) - len(new), 'missing_from_folder': gone,
                      'to_stage': sorted(set(stage))}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
