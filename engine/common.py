"""Outils partagés du moteur Studio Vidéo."""
import json, os, subprocess, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = Path(os.environ.get('STUDIO_MODELS', '/tmp/studio-models'))
VIDEO_EXT = {'.mp4', '.mov', '.m4v', '.mkv', '.avi', '.webm'}
AUDIO_EXT = {'.wav', '.mp3', '.m4a', '.aac', '.flac', '.ogg'}
FORMATS = {'9:16': (1080, 1920), '1:1': (1080, 1080), '16:9': (1920, 1080), '4:5': (1080, 1350)}
FPS = 30


def run(cmd, check=True, text=True, **kw):
    r = subprocess.run(cmd, capture_output=True, text=text, **kw)
    if check and r.returncode != 0:
        err = r.stderr if text else r.stderr.decode('utf-8', 'replace')
        raise RuntimeError(f"Commande échouée : {' '.join(map(str, cmd))[:300]}\n{err[-1500:]}")
    return r


def probe(path):
    """Durée, taille affichée (rotation incluse), fps, présence d'audio."""
    r = run(['ffprobe', '-v', 'error', '-print_format', 'json', '-show_format', '-show_streams', str(path)])
    m = json.loads(r.stdout)
    v = next((s for s in m['streams'] if s['codec_type'] == 'video'), None)
    a = any(s['codec_type'] == 'audio' for s in m['streams'])
    if v is None:
        return {'duration': float(m['format'].get('duration', 0)), 'width': 0, 'height': 0, 'fps': 0, 'has_audio': a}
    w, h = int(v['width']), int(v['height'])
    rot = 0
    for sd in v.get('side_data_list', []) or []:
        if 'rotation' in sd:
            rot = int(float(sd['rotation']))
    rot = int(v.get('tags', {}).get('rotate', rot))
    if abs(rot) % 180 == 90:
        w, h = h, w
    num, den = (v.get('avg_frame_rate') or '0/1').split('/')
    fps = float(num) / float(den) if float(den) else 0.0
    dur = float(v.get('duration') or m['format'].get('duration') or 0)
    return {'duration': round(dur, 3), 'width': w, 'height': h, 'fps': round(fps, 3), 'has_audio': a}


def file_key(path):
    st = os.stat(path)
    return f"{Path(path).name}|{st.st_size}|{int(st.st_mtime)}"


def short_hash(text, n=8):
    return hashlib.sha1(text.encode()).hexdigest()[:n]


def load_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding='utf-8'))


def save_json(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(p)


def library(kind, name):
    """Charge une fiche de la bibliothèque : kind = styles | compositions | brand."""
    p = ROOT / 'library' / kind / f'{name}.json'
    if not p.exists():
        avail = sorted(x.stem for x in (ROOT / 'library' / kind).glob('*.json'))
        raise FileNotFoundError(f"{kind}/{name} introuvable. Disponibles : {', '.join(avail)}")
    return json.loads(p.read_text(encoding='utf-8'))


def fmt_t(s):
    s = max(0.0, float(s))
    return f"{int(s // 60)}:{s % 60:05.2f}"
