"""Indexe un dossier de rushes en segments notés. Incrémental : seuls les fichiers
nouveaux ou modifiés sont analysés, les autres sont repris de l'index existant.

Usage :
  python3 engine/index_rushes.py <dossier_rushes> [--index <fichier.json>] [--no-asr] [--lang fr]

Sortie : <dossier>/_studio/index.json + une planche d'images par fichier
(<dossier>/_studio/sheets/<FID>_<n>.jpg) que Claude regarde pour décrire les segments
(voir engine/annotate.py).
"""
import argparse, sys, numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path(__file__).parent))
from common import run, probe, file_key, load_json, save_json, VIDEO_EXT, MODELS, fmt_t

AN_W, AN_FPS = 192, 4          # analyse : 4 images/s, 192 px de large
SEG_MIN, SEG_MAX, SEG_WIN = 0.8, 6.0, 4.0


# ---------------------------------------------------------------- image
def gray_frames(path, w, h):
    hh = int(round(AN_W * h / max(w, 1) / 2) * 2) or AN_W
    r = run(['ffmpeg', '-v', 'error', '-i', str(path), '-vf', f'fps={AN_FPS},scale={AN_W}:{hh},format=gray',
             '-f', 'rawvideo', '-'], text=False)
    a = np.frombuffer(r.stdout, dtype=np.uint8)
    n = len(a) // (AN_W * hh)
    return a[: n * AN_W * hh].reshape(n, hh, AN_W).astype(np.float32)


def sharpness(f):
    lap = -4 * f[1:-1, 1:-1] + f[:-2, 1:-1] + f[2:, 1:-1] + f[1:-1, :-2] + f[1:-1, 2:]
    return float(lap.var())


def shift(a, b):
    """Décalage global entre deux images (corrélation de phase)."""
    F = np.fft.fft2(a - a.mean()) * np.conj(np.fft.fft2(b - b.mean()))
    c = np.fft.ifft2(F / (np.abs(F) + 1e-6)).real
    y, x = np.unravel_index(np.argmax(c), c.shape)
    if y > c.shape[0] // 2: y -= c.shape[0]
    if x > c.shape[1] // 2: x -= c.shape[1]
    return float(x), float(y)


def frame_metrics(fr):
    n = len(fr)
    sharp = np.array([sharpness(x) for x in fr]) if n else np.zeros(0)
    bright = fr.reshape(n, -1).mean(1) if n else np.zeros(0)
    motion = np.zeros(n); sh = np.zeros((n, 2))
    for i in range(1, n):
        motion[i] = float(np.abs(fr[i] - fr[i - 1]).mean())
        sh[i] = shift(fr[i - 1], fr[i])
    return sharp, bright, motion, sh


# ---------------------------------------------------------------- son
_vad = _asr = None


def speech_regions(path, lang, use_asr):
    """Zones de parole (VAD) et leur transcription (Whisper)."""
    global _vad, _asr
    import sherpa_onnx
    raw = run(['ffmpeg', '-v', 'error', '-i', str(path), '-vn', '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'], check=False, text=False).stdout
    a = np.frombuffer(raw, dtype=np.float32)
    if len(a) < 16000:
        return []
    cfg = sherpa_onnx.VadModelConfig()
    cfg.silero_vad.model = str(MODELS / 'silero_vad.onnx')
    cfg.silero_vad.min_silence_duration = 0.25
    cfg.silero_vad.max_speech_duration = 8
    cfg.sample_rate = 16000
    vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=int(len(a) / 16000) + 30)
    ws = cfg.silero_vad.window_size
    segs = []
    for i in range(0, len(a) - ws, ws):
        vad.accept_waveform(a[i:i + ws])
        while not vad.empty():
            segs.append((vad.front.start, len(vad.front.samples))); vad.pop()
    vad.flush()
    while not vad.empty():
        segs.append((vad.front.start, len(vad.front.samples))); vad.pop()
    if use_asr and _asr is None:
        M = MODELS / 'sherpa-onnx-whisper-small'
        _asr = sherpa_onnx.OfflineRecognizer.from_whisper(
            encoder=str(M / 'small-encoder.int8.onnx'), decoder=str(M / 'small-decoder.int8.onnx'),
            tokens=str(M / 'small-tokens.txt'), num_threads=2, language=lang or '', task='transcribe')
    out = []
    for st, n in segs:
        if n < 4800:
            continue
        text, lg = '', ''
        if use_asr:
            s = _asr.create_stream(); s.accept_waveform(16000, a[st:st + n]); _asr.decode_stream(s)
            text, lg = s.result.text.strip(), s.result.lang
        t0, t1 = st / 16000, (st + n) / 16000
        out.append({'start': round(t0, 2), 'end': round(t1, 2), 'text': text, 'lang': lg, 'words': timed_words(text, t0, t1)})
    return out


def timed_words(text, t0, t1):
    """Horodatage approché des mots : réparti selon la longueur des mots (+ pauses aux ponctuations)."""
    ws = text.split()
    if not ws:
        return []
    weight = [len(w) + 1.5 + (3 if w[-1] in '.!?' else 1.5 if w[-1] in ',;:' else 0) for w in ws]
    tot, acc, out = sum(weight), 0.0, []
    span = max(0.1, t1 - t0 - 0.1)
    for w, k in zip(ws, weight):
        a = t0 + 0.05 + span * acc / tot
        acc += k
        out.append([w, round(a, 2), round(t0 + 0.05 + span * (acc - (3 if w[-1] in '.!?' else 1.5 if w[-1] in ',;:' else 0)) / tot, 2)])
    return out


# ---------------------------------------------------------------- découpage
def shot_cuts(path, dur):
    r = run(['ffmpeg', '-hide_banner', '-i', str(path), '-vf', "scale=320:-2,select='gt(scene,0.3)',showinfo", '-an', '-f', 'null', '-'], check=False)
    import re
    cuts = [float(x) for x in re.findall(r'pts_time:([0-9.]+)', r.stderr)]
    out = []
    for c in cuts:
        if 0.3 < c < dur - 0.3 and (not out or c - out[-1] > 0.5):
            out.append(c)
    return out


def segment(dur, cuts, speech):
    """Coupes de plan + bords des zones de parole, puis fenêtres de 4 s pour les longs passages muets."""
    b = {0.0, dur} | set(cuts)
    for s in speech:
        b.add(max(0.0, s['start'] - 0.15)); b.add(min(dur, s['end'] + 0.25))
    b = sorted(b)
    pieces = []
    for a, z in zip(b, b[1:]):
        talk = any(s['start'] < z and s['end'] > a for s in speech)
        if z - a > SEG_MAX and not talk:
            k = max(2, round((z - a) / SEG_WIN))
            step = (z - a) / k
            pieces += [(a + i * step, a + (i + 1) * step) for i in range(k)]
        else:
            pieces.append((a, z))
    merged = []
    for a, z in pieces:
        if merged and (z - a < SEG_MIN or merged[-1][1] - merged[-1][0] < SEG_MIN) and a not in cuts:
            merged[-1] = (merged[-1][0], z)
        else:
            merged.append((a, z))
    return [(round(a, 2), round(z, 2)) for a, z in merged if z - a >= 0.4]


def score(sharp, bright, jitter):
    q, why = 5, []
    if sharp < 25: q -= 2; why.append('flou')
    elif sharp < 60: q -= 1; why.append('peu net')
    if bright < 25: q -= 2; why.append('très sombre')
    elif bright < 45: q -= 1; why.append('sombre')
    elif bright > 215: q -= 1; why.append('surexposé')
    if jitter > 3: q -= 2; why.append('tremblé')
    elif jitter > 1.5: q -= 1; why.append('un peu tremblé')
    return max(1, q), why


# ---------------------------------------------------------------- planche
def contact_sheets(path, fid, segs, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    tw, cols = 300, 5
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
    except OSError:
        font = ImageFont.load_default()
    thumbs = []
    for s in segs:
        t = (s['start'] + s['end']) / 2
        r = run(['ffmpeg', '-v', 'error', '-ss', f'{t:.2f}', '-i', str(path), '-frames:v', '1', '-vf', f'scale={tw}:-2', '-f', 'image2pipe', '-vcodec', 'png', '-'], check=False, text=False)
        try:
            import io
            im = Image.open(io.BytesIO(r.stdout)).convert('RGB')
        except Exception:
            im = Image.new('RGB', (tw, int(tw * 16 / 9)), 'gray')
        d = ImageDraw.Draw(im)
        label = f"{s['id']}  {fmt_t(s['start'])}-{fmt_t(s['end'])}  q{s['quality']}{'  🗣' if s['has_speech'] else ''}"
        d.rectangle([0, 0, im.width, 24], fill=(0, 0, 0))
        d.text((6, 3), label.replace('🗣', 'VOIX'), fill=(255, 255, 255), font=font)
        thumbs.append(im)
    files = []
    for k in range(0, len(thumbs), 20):
        chunk = thumbs[k:k + 20]
        th = max(t.height for t in chunk)
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * tw, rows * th), 'white')
        for i, t in enumerate(chunk):
            sheet.paste(t, ((i % cols) * tw, (i // cols) * th))
        p = out_dir / f'{fid}_{k // 20 + 1}.jpg'
        sheet.save(p, quality=82)
        files.append(str(p))
    return files


# ---------------------------------------------------------------- principal
def index_file(path, fid, lang, use_asr, sheets_dir):
    info = probe(path)
    dur = info['duration']
    fr = gray_frames(path, info['width'], info['height'])
    sharp, bright, motion, sh = frame_metrics(fr)
    speech = speech_regions(path, lang, use_asr) if info['has_audio'] else []
    cuts = shot_cuts(path, dur)
    segs = []
    for n, (a, z) in enumerate(segment(dur, cuts, speech), 1):
        i0, i1 = int(a * AN_FPS), max(int(a * AN_FPS) + 1, int(z * AN_FPS))
        s_sh = float(np.median(sharp[i0:i1])) if i1 <= len(sharp) and i1 > i0 else 0.0
        s_br = float(np.mean(bright[i0:i1])) if i1 <= len(bright) and i1 > i0 else 0.0
        pos = np.cumsum(sh[i0:i1], axis=0)
        jit = 0.0
        if len(pos) > 4:
            k = np.ones(5) / 5
            smooth = np.stack([np.convolve(pos[:, j], k, mode='same') for j in range(2)], 1)
            jit = float(np.abs(pos - smooth)[2:-2].mean()) * (1920 / AN_W) / 4   # en px ~1080p
        mov = float(np.mean(motion[i0:i1])) if i1 <= len(motion) and i1 > i0 else 0.0
        q, why = score(s_sh, s_br, jit)
        talk = [s for s in speech if s['start'] < z and s['end'] > a]
        segs.append({
            'id': f'{fid}.S{n:02d}', 'file': fid, 'start': a, 'end': z, 'dur': round(z - a, 2),
            'has_speech': bool(talk),
            'transcript': ' '.join(w[0] for s in talk for w in s['words'] if a <= (w[1] + w[2]) / 2 < z).strip(),
            'speech': [[max(a, s['start']), min(z, s['end'])] for s in talk],
            'sharpness': round(s_sh, 1), 'brightness': round(s_br, 1), 'motion': round(mov, 2), 'jitter': round(jit, 2),
            'quality': q, 'issues': why, 'usable': q >= 3 and z - a >= SEG_MIN,
            'description': '', 'framing': '', 'tags': [], 'people': [], 'products': [], 'used_in': [],
        })
    files = contact_sheets(path, fid, segs, sheets_dir)
    return info, speech, segs, files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('--index')
    ap.add_argument('--lang', default='')
    ap.add_argument('--no-asr', action='store_true')
    a = ap.parse_args()
    folder = Path(a.folder).resolve()
    idx_path = Path(a.index) if a.index else folder / '_studio' / 'index.json'
    idx = load_json(idx_path, {'version': 1, 'files': {}, 'segments': {}})
    vids = sorted(p for p in folder.rglob('*') if p.suffix.lower() in VIDEO_EXT and '_studio' not in p.parts)
    known = {f['key']: fid for fid, f in idx['files'].items()}
    used_ids = set(idx['files'])
    todo = []
    for p in vids:
        k = file_key(p)
        if k in known:
            idx['files'][known[k]]['path'] = str(p)
            continue
        old = next((fid for fid, f in idx['files'].items() if f['name'] == p.name), None)
        if old:   # fichier modifié : on remplace ses segments
            idx['segments'] = {sid: s for sid, s in idx['segments'].items() if s['file'] != old}
            fid = old
        else:
            n = len(used_ids) + 1
            while f'F{n:03d}' in used_ids: n += 1
            fid = f'F{n:03d}'; used_ids.add(fid)
        todo.append((p, fid, k))
    print(f'{len(vids)} vidéos, {len(vids) - len(todo)} déjà indexées, {len(todo)} à analyser', flush=True)
    for p, fid, k in todo:
        info, speech, segs, sheets = index_file(p, fid, a.lang, not a.no_asr, idx_path.parent / 'sheets')
        idx['files'][fid] = {'name': p.name, 'path': str(p), 'key': k, **info, 'speech': speech, 'sheets': sheets,
                             'n_segments': len(segs), 'summary': ''}
        for s in segs:
            idx['segments'][s['id']] = s
        save_json(idx_path, idx)
        ok = sum(s['usable'] for s in segs)
        print(f"  {fid} {p.name}: {info['duration']:.1f}s {info['width']}x{info['height']} · {len(segs)} segments ({ok} exploitables) · {len(speech)} zones de parole", flush=True)
    missing = [fid for fid, f in idx['files'].items() if not Path(f['path']).exists()]
    if missing:
        print(f'  Absents du dossier (conservés dans l\'index) : {", ".join(missing)}')
    save_json(idx_path, idx)
    print(f'Index : {idx_path}')


if __name__ == '__main__':
    main()
