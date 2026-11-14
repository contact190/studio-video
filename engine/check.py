"""Contrôle qualité automatique d'une vidéo produite.

Usage : python3 engine/check.py <video.mp4> [--report <video.report.json>] [--format 9:16]
Vérifie : format, cadence, durée, son présent et volume (-14 LUFS ±2), images noires ou figées,
plans répétés. Sort une planche d'images (1/s) à regarder avant de livrer.
"""
import argparse, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import run, probe, FORMATS


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('video'); ap.add_argument('--report'); ap.add_argument('--format', default='9:16')
    a = ap.parse_args()
    v = Path(a.video); rep = Path(a.report) if a.report else v.with_name(v.name.replace('_preview', '').replace('.mp4', '.report.json'))
    res, ok = [], True

    def check(cond, label, detail=''):
        nonlocal ok
        ok &= bool(cond); res.append(('OK ' if cond else 'ÉCHEC') + f' · {label}' + (f' ({detail})' if detail else ''))

    info = probe(v)
    W, H = FORMATS[a.format]
    preview = '_preview' in v.name
    if preview: W, H = W // 2, H // 2
    check((info['width'], info['height']) == (W, H), f'format {a.format}', f"{info['width']}x{info['height']}")
    check(abs(info['fps'] - 30) < 0.1, 'cadence 30 i/s', f"{info['fps']}")
    check(info['has_audio'], 'piste son présente')
    r = run(['ffmpeg', '-hide_banner', '-i', str(v), '-af', 'ebur128', '-f', 'null', '-'], check=False)
    m = re.findall(r'I:\s+(-?[\d.]+) LUFS', r.stderr)
    lufs = float(m[-1]) if m else -99
    check(-16.5 <= lufs <= -11.5, 'volume sonore', f'{lufs} LUFS, cible -14')
    r = run(['ffmpeg', '-hide_banner', '-i', str(v), '-vf', 'blackdetect=d=0.4:pix_th=0.06', '-an', '-f', 'null', '-'], check=False)
    blacks = re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', r.stderr)
    check(not blacks, 'pas d\'écran noir', ', '.join(f'{float(x):.1f}-{float(y):.1f}s' for x, y in blacks))
    r = run(['ffmpeg', '-hide_banner', '-i', str(v), '-vf', 'freezedetect=n=0.002:d=1.5', '-an', '-f', 'null', '-'], check=False)
    fr = re.findall(r'freeze_start: ([\d.]+)', r.stderr)
    res.append(('INFO' if fr else 'OK ') + ' · image figée > 1,5 s' + (f" à {', '.join(f'{float(x):.1f}s' for x in fr)} (normal sur un carton final)" if fr else ''))
    if rep.exists():
        R = json.loads(rep.read_text())
        segs = [e['segment'] for e in R['edit']]
        dup = sorted({s for s in segs if segs.count(s) > 1})
        check(not dup, 'aucun plan répété', ', '.join(dup))
        for w in R.get('warnings', []):
            res.append('INFO · ' + w)
    sheet = v.with_name(v.stem + '_planche.jpg')
    run(['ffmpeg', '-v', 'error', '-y', '-i', str(v), '-vf', "fps=1,scale=180:-2,tile=8x6", '-frames:v', '1', '-q:v', '3', str(sheet)])
    print('\n'.join(res)); print(f'Planche à regarder : {sheet}')
    print('RÉSULTAT :', 'OK' if ok else 'À CORRIGER')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
