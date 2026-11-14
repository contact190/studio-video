"""Musique de secours générée par code (gratuite), quand aucun fichier n'est fourni.
Énergie haute sur les zones « punchy », plus calme sous les explications.

Usage : python3 engine/music.py <sortie.wav> <durée_s> [--calm a-b,c-d] [--hits t1,t2]
"""
import sys, wave, argparse, numpy as np
from scipy.signal import butter, sosfilt

SR = 48000


def make(out, dur, calm=(), hits=(), bpm=120, seed=7):
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    N = int(SR * dur); L = np.zeros(N); R = np.zeros(N)
    lp = lambda x, f: sosfilt(butter(2, f, 'low', fs=SR, output='sos'), x)
    hp = lambda x, f: sosfilt(butter(4, f, 'high', fs=SR, output='sos'), x)
    bp = lambda x, a, b: sosfilt(butter(2, [a, b], 'band', fs=SR, output='sos'), x)
    env = lambda n, a, d: np.minimum(1, np.arange(n) / SR / max(a, 1e-4)) * np.exp(-np.arange(n) / SR / d)

    def add(sig, t, gl=1.0, gr=None):
        i = int(t * SR); j = min(N, i + len(sig))
        if 0 <= i < N:
            L[i:j] += sig[:j - i] * gl; R[i:j] += sig[:j - i] * (gl if gr is None else gr)

    def kick(g):
        n = int(.45 * SR); t = np.arange(n) / SR
        return np.sin(2 * np.pi * np.cumsum(45 + 95 * np.exp(-t / .045)) / SR) * np.exp(-t / .22) * g
    def clap(g):
        n = int(.25 * SR); return bp(rng.normal(0, 1, n), 900, 4500) * env(n, .001, .06) * .45 * g
    def hat(g):
        n = int(.05 * SR); return hp(rng.normal(0, 1, n), 7500) * env(n, .0005, .012) * .22 * g
    note = lambda m: 440 * 2 ** ((m - 69) / 12)
    saw = lambda f, n, d=0: 2 * ((np.arange(n) / SR * f * (1 + d)) % 1) - 1
    def bass(m, d, g=1):
        n = int(d * SR); return lp(saw(note(m), n) * .6 + np.sin(2 * np.pi * note(m - 12) * np.arange(n) / SR), 380) * env(n, .004, d * .6) * .32 * g
    def pluck(m, g=1):
        n = int(.4 * SR); t = np.arange(n) / SR
        return (np.sin(2 * np.pi * note(m) * t) + .35 * np.sin(4 * np.pi * note(m) * t)) * env(n, .002, .11) * .16 * g
    def pad(ms, d, g=1):
        n = int(d * SR); l = sum(saw(note(m), n, -.004) + saw(note(m), n, .003) for m in ms); r = sum(saw(note(m), n, .004) + saw(note(m), n, -.002) for m in ms)
        e = np.minimum(1, np.arange(n) / (.35 * SR)) * np.minimum(1, (n - np.arange(n)) / (.3 * SR))
        return lp(l, 1400) * e * .035 * g, lp(r, 1400) * e * .035 * g
    def impact(g=1):
        n = int(2 * SR); t = np.arange(n) / SR
        return (np.sin(2 * np.pi * (38 + 30 * np.exp(-t / .08)) * t) * np.exp(-t / .7) * .9 + lp(rng.normal(0, 1, n), 2500) * np.exp(-t / .35) * .5) * .6 * g

    is_calm = lambda t: any(a <= t < b for a, b in calm)
    prog = [(57, [69, 72, 76]), (53, [69, 72, 77]), (48, [67, 72, 76]), (55, [67, 71, 74])]
    for b in range(int(dur / beat)):
        t = b * beat
        if t > dur - 2: break
        root, ch = prog[(b // 8) % 4]; bb = b % 4
        if not is_calm(t):
            add(kick(.95), t)
            if bb in (1, 3): add(clap(1), t)
            add(hat(.9), t + beat / 2, .8, 1); add(hat(.6), t, 1, .8)
            add(bass(root - 12, beat * .45), t); add(bass(root - 12, beat * .4), t + beat / 2)
            add(pluck(ch[b % 3] + 12, .9), t + beat / 2, .7, 1)
        else:
            if bb in (0, 2): add(kick(.55), t)
            add(hat(.35), t + beat / 2, .9, .6)
            if bb == 0: add(bass(root - 12, beat * 1.6, .8), t)
            for k, m in enumerate([ch[0], ch[1], ch[2], ch[1]]):
                add(pluck(m + 12, .75), t + k * beat / 4, .6 + .2 * (k % 2), .8 - .2 * (k % 2))
        if b % 8 == 0:
            l, r = pad([c - 12 for c in ch], 8 * beat, .8)
            i = int(t * SR); j = min(N, i + len(l)); L[i:j] += l[:j - i]; R[i:j] += r[:j - i]
    for t in hits:
        add(impact(), t)
    mix = np.tanh(np.stack([L, R], 1) * 1.6) / np.tanh(1.6)
    fn = int(1.2 * SR); mix[-fn:] *= np.linspace(1, 0, fn)[:, None]
    mix = mix / max(1e-6, np.abs(mix).max()) * .89
    with wave.open(str(out), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype('<i2').tobytes())


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('dur', type=float)
    ap.add_argument('--calm', default=''); ap.add_argument('--hits', default='')
    a = ap.parse_args()
    calm = [tuple(map(float, x.split('-'))) for x in a.calm.split(',') if x]
    make(a.out, a.dur, calm, [float(x) for x in a.hits.split(',') if x])
