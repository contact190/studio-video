"""Pont vers rea-video (github.com/JuneYaooo/rea-video) pour l'analyse des rushes.

rea-video apporte, plan par plan : les coupes, la taille de plan, la position du sujet
(utile pour recadrer en 9:16), le mouvement de caméra, les visages, le texte déjà incrusté
dans l'image et une estimation de l'origine (filmé / généré). Sa transcription n'est pas
utilisée : Whisper s'en charge, avec l'horodatage mot par mot.
"""
import json, os, shutil
from pathlib import Path
from common import run

REA_DIR = Path(os.environ.get('REA_VIDEO_DIR', '/tmp/rea-video'))
REA_BIN = REA_DIR / '.venv' / 'bin' / 'rea-video'


def available():
    return REA_BIN.exists()


def analyse(video, out_dir, stems=False):
    """Lance rea-video et renvoie le contenu de breakdown.json (ou None si échec)."""
    out_dir = Path(out_dir)
    tmp = out_dir.with_name(out_dir.name + '.work')
    shutil.rmtree(tmp, ignore_errors=True)
    cmd = [str(REA_BIN), 'decompose', str(video), '-o', str(tmp), '--lang', 'en',
           '--no-packaging', '--no-asr', '--no-whole', '--no-vlm']
    if not stems:
        cmd.append('--no-stems')
    r = run(cmd, check=False, timeout=3600)
    bd = tmp / 'breakdown.json'
    if r.returncode != 0 or not bd.exists():
        shutil.rmtree(tmp, ignore_errors=True)
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(bd, out_dir / 'breakdown.json')      # on ne garde que le résumé (léger)
    shutil.rmtree(tmp, ignore_errors=True)
    return json.loads((out_dir / 'breakdown.json').read_text(encoding='utf-8'))


def shots(bd):
    """Résumé utile de chaque plan."""
    out = []
    for s in bd.get('shots', []):
        a = s.get('aspects', {})
        fm = a.get('framing', {}).get('measured', {}); fr = a.get('framing', {}).get('result', {})
        cm = a.get('camera', {}).get('measured', {}); cr = a.get('camera', {}).get('result', {})
        texts = [t for tr in s.get('text', {}).get('tracks', []) for t in tr.get('texts', [])]
        out.append({
            'start': s['start'], 'end': s['end'],
            'shot_size': fr.get('shot_size') or fm.get('shot_size'), 'subject': fr.get('subject') or fm.get('subject'),
            'center_x': fm.get('center_x'), 'center_y': fm.get('center_y'), 'faces': s.get('faces'),
            'camera': cr.get('move') or cm.get('motion') or cr.get('support'), 'shake': cm.get('shake'),
            'overlay_text': texts[:6], 'origin': (s.get('material') or {}).get('origin'),
        })
    return out


def summary(bd):
    au = bd.get('audio', {})
    return {'verdict': bd.get('summary', {}).get('verdict', ''),
            'voice_ratio': (au.get('voice') or {}).get('ratio'),
            'music': (au.get('music') or {}).get('present')}


def best_shot(shot_list, a, z):
    best, ov = None, 0.0
    for s in shot_list:
        o = min(z, s['end']) - max(a, s['start'])
        if o > ov:
            best, ov = s, o
    return best
