#!/usr/bin/env python3
"""Recaler les mots sur le son : chaque fin de phrase est placée sur un vrai silence.

Whisper (sherpa-onnx) ne donne pas l'heure de chaque mot : l'index les répartit dans chaque zone de
parole. Ici, on repère les silences à l'intérieur de chaque zone, on y place les fins de phrase
(dans l'ordre, au plus près de leur estimation), puis on répartit les mots dans chaque phrase.
Les coupes et les sous-titres tombent alors sur les pauses réelles.

Usage : python3 engine/realign.py <index.json>   (met l'index à jour sur place ; idempotent)
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HOP = 0.02


def energy(path):
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vn', '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'],
                         capture_output=True).stdout
    x = np.frombuffer(pcm, np.float32)
    n = len(x) // 320
    return np.sqrt((x[:n * 320].reshape(n, 320) ** 2).mean(1)) if n else np.zeros(1)


def pauses(e, t0, t1, min_len=0.12):
    """Milieux des silences d'au moins `min_len` s entre t0 et t1."""
    a, b = int(t0 / HOP), int(t1 / HOP)
    seg = e[a:b]
    if len(seg) < 5:
        return []
    thr = max(0.006, np.percentile(seg, 20) * 1.8)
    quiet = seg < thr
    out, i = [], 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]:
                j += 1
            if (j - i) * HOP >= min_len and i > 0 and j < len(quiet):
                out.append(((a + (i + j) / 2) * HOP, (j - i) * HOP))
            i = j
        else:
            i += 1
    return out


def spread(words, t0, t1):
    weight = [len(w) + 1.5 for w in words]
    tot, acc, res = sum(weight), 0.0, []
    span = max(0.1, t1 - t0)
    for w, k in zip(words, weight):
        a = t0 + span * acc / tot
        acc += k
        res.append([w, round(a, 2), round(t0 + span * acc / tot - 0.03, 2)])
    return res


def realign_region(e, sp):
    words = [w[0] for w in sp.get('words', [])]
    if len(words) < 3:
        return sp.get('words', [])
    t0, t1 = sp['start'], sp['end']
    cuts = [i for i, w in enumerate(words[:-1]) if w[-1] in '.!?,;:']
    ps = pauses(e, t0, t1)
    if not cuts or not ps:
        return spread(words, t0 + 0.03, t1 - 0.03)
    est = {i: w[2] for i, w in enumerate(sp['words'])}
    # fins de phrase d'abord, puis virgules ; chaque pause sert une fois, ordre conservé
    chosen, used = {}, set()
    for i in sorted(cuts, key=lambda i: (words[i][-1] not in '.!?', i)):
        cands = [(abs(p - est[i]), p) for p, _ in ps if p not in used and abs(p - est[i]) < 1.2]
        if not cands:
            continue
        p = min(cands)[1]
        before = [chosen[k] for k in chosen if k < i]
        after = [chosen[k] for k in chosen if k > i]
        if (before and p <= max(before)) or (after and p >= min(after)):
            continue
        chosen[i] = p
        used.add(p)
    bounds = [(-1, t0 + 0.03)] + sorted(chosen.items()) + [(len(words) - 1, t1 - 0.03)]
    out = []
    for (i, a), (j, b) in zip(bounds, bounds[1:]):
        out += spread(words[i + 1:j + 1], a + (0.06 if i >= 0 else 0), b - (0.06 if j < len(words) - 1 else 0))
    return out


def main():
    p = Path(sys.argv[1])
    idx = json.loads(p.read_text(encoding='utf-8'))
    n = 0
    for fid, f in idx['files'].items():
        if f.get('aligned') or not f.get('speech') or not Path(f.get('path', '')).exists():
            continue
        e = energy(f['path'])
        for sp in f['speech']:
            sp['words'] = realign_region(e, sp)
        f['aligned'] = True
        n += 1
    for s in idx['segments'].values():
        f = idx['files'][s['file']]
        if f.get('speech'):
            s['transcript'] = ' '.join(w[0] for sp in f['speech'] for w in sp['words']
                                       if s['start'] <= (w[1] + w[2]) / 2 < s['end']).strip()
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(p)
    print(f'{n} fichiers recalés')


if __name__ == '__main__':
    main()
