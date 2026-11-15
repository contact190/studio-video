#!/usr/bin/env python3
"""Variantes : répartir N vidéos sur la bibliothèque, résumer, monter en série.

  matrix  <index> --n 20 [--style auto|id] [--composition auto|id] [--must F003,F002.S06]
          [--project nom] [--out variants.json]
      → variants.json : une ligne par variante (nom, style, composition, personne principale,
        plans imposés). En « auto », seules les compositions que les rushes permettent.
  draft   <variants.json> <brief.json> [--out plans]
      → un premier jet de plan par variante (accroche, témoignages de la personne principale,
        plans de démo tournants, voix off tirée des messages du brief, carton final). Claude le relit.
  names   <variants.json> --date 11.10.26 --product 001 --ident ryad [--existing listing.json] [--only V01,V03]
      → nom final de chaque variante validée : 11.10.26_001_ryad_Videoask_V<x>, x continue après la
        dernière version trouvée dans SORTIES.
  board   <variants.json> [--plans dossier]
      → planche de résumé (Markdown) : nom, style, composition, personne, accroche, durée.
  build   <dossier de plans> [--final] [--only V01,V04] [--out dossier]
      → monte chaque plan l'un après l'autre (aperçu par défaut) et résume.
"""
import argparse
import itertools
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / 'library'
DEMO_TAGS = {'demo', 'démo', 'produit', 'product', 'broll', 'b-roll', 'test', 'preuve'}


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def material(index):
    """Ce que les rushes permettent : personnes qui parlent, plans de démo, concurrent."""
    people, demo, competitor = {}, 0, 0
    for s in index['segments'].values():
        if not s.get('usable', True) or 'texte incrusté' in s.get('issues', []):
            continue
        tags = {t.lower() for t in s.get('tags', [])}
        if s.get('has_speech') and s.get('people'):
            for p in s['people']:
                people[p] = people.get(p, 0) + s.get('dur', 0)
        elif tags & DEMO_TAGS or not s.get('has_speech'):
            demo += 1
        if 'concurrent' in tags or 'competitor' in tags:
            competitor += 1
    return {'people': people, 'demo': demo, 'competitor': competitor}


def fits(comp, mat):
    r = comp.get('requires', {})
    speakers = [p for p, d in mat['people'].items() if d >= r.get('speech_per_person', 0)]
    return (len(speakers) >= r.get('people', 0)
            and mat['demo'] >= r.get('demo_shots', 0)
            and mat['competitor'] >= r.get('competitor_shots', 0)
            and max(mat['people'].values() or [0]) >= r.get('longest_speech', 0))


def entries(kind):
    out = []
    for p in sorted((LIB / kind).glob('*.json')):
        d = load(p)
        out.append(d | {'id': d.get('id', p.stem)})
    out.sort(key=lambda d: d.get('status') != 'validé')
    return out


def matrix(a):
    index = load(a.index)
    mat = material(index)
    styles = entries('styles') if a.style == 'auto' else [load(LIB / 'styles' / f'{a.style}.json') | {'id': a.style}]
    comps = entries('compositions') if a.composition == 'auto' else [load(LIB / 'compositions' / f'{a.composition}.json') | {'id': a.composition}]
    if a.composition == 'auto':
        ok = [c for c in comps if fits(c, mat)]
        skipped = [c['id'] for c in comps if c not in ok]
        comps = ok or comps[:1]
    else:
        skipped = []
    pairs = [(c, s) for c in comps for s in styles]
    # Alterner les compositions d'abord, puis les styles : les variantes voisines diffèrent le plus.
    pairs.sort(key=lambda cs: (styles.index(cs[1]) + comps.index(cs[0])) % max(len(styles), 1))
    people = sorted(mat['people'], key=lambda p: -mat['people'][p]) or ['—']
    must = [m for m in (a.must or '').split(',') if m]
    out = []
    turn = {}
    for i, (c, s) in enumerate(itertools.cycle(pairs), 1):
        if i > a.n:
            break
        need = c.get('requires', {}).get('longest_speech', 8)
        able = [p for p in people if mat['people'].get(p, 0) >= need] or people
        lead = able[turn.get(c['id'], 0) % len(able)]
        turn[c['id']] = turn.get(c['id'], 0) + 1
        vid = f'V{i:02d}'
        out.append({'id': vid, 'name': f'{a.project}_{vid}_{s["id"]}_{c["id"]}', 'style': s['id'],
                    'composition': c['id'], 'lead_person': lead, 'must': must, 'hook_angle': i,
                    'status': 'proposée'})
    res = {'project': a.project, 'index': str(Path(a.index).resolve()), 'n': a.n, 'material': mat,
           'compositions_skipped': skipped, 'variants': out}
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(out)} variantes → {a.out}')
    if skipped:
        print('Compositions écartées (rushes insuffisants) : ' + ', '.join(skipped))


def board(a):
    v = load(a.variants)
    plans = Path(a.plans) if a.plans else None
    rows = ['| Variante | Style | Composition | Personne | Accroche | Durée |', '|---|---|---|---|---|---|']
    for x in v['variants']:
        hook, dur = '—', '—'
        if plans and (plans / f"{x['name']}.json").exists():
            p = load(plans / f"{x['name']}.json")
            hook = p.get('hook_title', '—')
            dur = p.get('estimated_duration', '—')
        rows.append(f"| {x['id']} | {x['style']} | {x['composition']} | {x['lead_person']} | {hook} | {dur} |")
    md = '\n'.join(rows)
    Path(a.variants).with_suffix('.board.md').write_text(md, encoding='utf-8')
    print(md)


def build(a):
    plans = sorted(Path(a.plans).glob('*.json'))
    only = set((a.only or '').split(',')) - {''}
    done, failed = [], []
    for p in plans:
        if only and not any(f'_{o}_' in p.name for o in only):
            continue
        cmd = [sys.executable, str(ROOT / 'engine' / 'build.py'), str(p.resolve())] + (['--out', str(Path(a.out).resolve())] if a.out else [])
        if not a.final:
            cmd.append('--preview')
        r = subprocess.run(cmd, capture_output=True, text=True)
        (done if r.returncode == 0 else failed).append(p.stem)
        print(('OK    ' if r.returncode == 0 else 'ÉCHEC ') + p.stem + ('' if r.returncode == 0 else ' — ' + (r.stdout + r.stderr).strip().splitlines()[-1]))
    print(f'{len(done)} montées, {len(failed)} en échec')
    return 1 if failed else 0



# ---------- premier jet des plans ----------

def _speech_words(f, s):
    return [w for sp in f.get('speech', []) for w in sp.get('words', []) if s['start'] <= (w[1] + w[2]) / 2 < s['end']]


_AUDIO = {}


def _rms(path):
    """Énergie du son par tranches de 20 ms (mise en cache par fichier)."""
    if path not in _AUDIO:
        import numpy as np
        pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vn', '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'],
                             capture_output=True).stdout
        x = np.frombuffer(pcm, np.float32)
        n = len(x) // 320
        _AUDIO[path] = np.sqrt((x[:n * 320].reshape(n, 320) ** 2).mean(1)) if n else np.zeros(1)
    return _AUDIO[path]


def _snap(path, t, lo, hi, window=0.45):
    """Déplace une coupe vers le moment le plus silencieux autour de t (entre lo et hi)."""
    e = _rms(path)
    a, b = max(lo, t - window), min(hi, t + window)
    i0, i1 = int(a / 0.02), max(int(a / 0.02) + 1, int(b / 0.02))
    seg = e[i0:i1]
    if not len(seg):
        return t
    return round((i0 + int(seg.argmin())) * 0.02 + 0.01, 2)


def _cut(f, s, cap):
    """Une ou plusieurs phrases entières du segment, coupées sur des silences, au plus `cap` s.
    Renvoie (entrée, sortie, texte) ou None si le segment ne contient pas de phrase entière."""
    allw = [w for sp in f.get('speech', []) for w in sp.get('words', [])]
    if not allw:
        return (s['start'], min(s['end'], s['start'] + cap), s.get('transcript', '')) if not s.get('has_speech') else None
    # début de phrase : premier mot de la parole, après un silence de 0,3 s, ou après . ! ?
    cap1 = lambda w: w[0][:1].isupper()   # Whisper met une majuscule en début de phrase
    e = _rms(f['path'])
    loud_at = lambda t: float(e[min(len(e) - 1, max(0, int(t / 0.02)))]) > 0.03
    starts = {i for i in range(len(allw)) if cap1(allw[i]) and (allw[i - 1][0][-1] in '.!?' if i else True)
              and not (allw[i][1] < 0.3 and loud_at(0.02))}   # pas de début de fichier en pleine phrase
    ends = {i for i, w in enumerate(allw) if w[0][-1] in '.!?'} | {len(allw) - 1}
    inseg = [i for i, w in enumerate(allw) if s['start'] - 0.05 <= (w[1] + w[2]) / 2 < s['end'] + 0.05]
    best = None
    for i in inseg:
        if i not in starts:
            continue
        for j in inseg:
            if j < i or j not in ends:
                continue
            d = allw[j][2] - allw[i][1]
            if d <= cap and d >= 1.2 and (best is None or d > best[2]):
                best = (i, j, d)
        if best:
            break
    if not best:
        return None
    i, j, _ = best
    # les mots sont datés approximativement : chercher le vrai silence autour de la coupe
    t0 = _snap(f['path'], allw[i][1] - 0.1, max(0.0, allw[i][1] - 0.5), allw[i][1] + 0.2, window=0.5)
    t1 = _snap(f['path'], allw[j][2] + 0.1, allw[j][2] - 0.3, min(f.get('duration', 1e9), allw[j][2] + 0.6), window=0.6)
    return round(t0, 2), round(max(t1, t0 + 0.8), 2), ' '.join(w[0] for w in allw[i:j + 1])


def draft(a):
    v = load(a.variants)
    brief = load(a.brief)
    idx = load(v['index'])
    segs, files = idx['segments'], idx['files']
    out = Path(a.out)
    (out / 'audio').mkdir(parents=True, exist_ok=True)
    ok = lambda s: s.get('usable', True) and 'texte incrusté' not in s.get('issues', []) and s.get('quality', 3) >= 3
    speakers = {}
    for sid, s in segs.items():
        if ok(s) and s.get('has_speech') and s.get('people'):
            speakers.setdefault(s['people'][0], []).append(sid)
    demo = [sid for sid, s in segs.items() if ok(s) and not (s.get('has_speech') and s.get('people'))]
    demo.sort(key=lambda k: -segs[k].get('quality', 3))
    people = sorted(speakers, key=lambda p: -sum(segs[x]['dur'] for x in speakers[p]))
    msgs = brief.get('messages', []) + brief.get('proofs', [])
    hooks = brief.get('hooks', []) or [brief.get('subject', '')]
    for n, x in enumerate(v['variants']):
        comp = load(LIB / 'compositions' / f"{x['composition']}.json")
        lead = x['lead_person'] if x['lead_person'] in speakers else (people[0] if people else None)
        others = [p for p in people if p != lead]
        used, d_ptr, m_ptr, total = set(), n * 3, n, 0.0
        must = []
        for m in x.get('must', []):
            if m in segs:
                must.append(m)
            else:
                cands = [k for k in segs if segs[k]['file'] == m and ok(segs[k])]
                if cands:
                    must.append(max(cands, key=lambda k: segs[k].get('quality', 3)))
        plan = {'title': x['name'], 'style': x['style'], 'composition': x['composition'],
                'brand': brief.get('brand', 'neutre'), 'format': brief.get('format', '9:16'),
                'rushes_index': v['index'], 'voice': {'voice': 'am_michael', 'speed': 1.05}, 'music': 'auto',
                'hook_title': hooks[(x['hook_angle'] - 1) % len(hooks)], 'slots': {}, 'draft': True}

        def take_demo(k):
            nonlocal d_ptr
            res = []
            pool = [m for m in must if m not in used and not segs[m].get('has_speech')] + demo
            for sid in pool:
                if len(res) >= k:
                    break
                if sid in used:
                    continue
                res.append({'seg': sid}); used.add(sid)
            if len(res) < k:   # tourner dans les plans de démo
                for i in range(len(demo)):
                    sid = demo[(d_ptr + i) % len(demo)]
                    if sid not in used:
                        res.append({'seg': sid}); used.add(sid)
                    if len(res) >= k:
                        break
            d_ptr += k
            return res

        def speak(person, target, cap=6.0, rotate=0, max_clips=99):
            clips, dur = [], 0.0
            pool = [m for m in must if m not in used and segs[m].get('has_speech')]
            own = sorted(speakers.get(person, []), key=lambda k: (segs[k]['file'], segs[k]['start']))
            if own and rotate:
                r = rotate % len(own)
                own = own[r:] + own[:r]
            pool += own
            for sid in pool:
                if dur >= target or sid in used or len(clips) >= max_clips:
                    continue
                s = segs[sid]
                r = _cut(files[s['file']], s, min(cap, target - dur + 1.5))
                if not r or r[1] - r[0] < 1.0:
                    continue
                t0, t1, _ = r
                clips.append({'seg': sid, 'in': t0, 'out': t1}); used.add(sid); dur += t1 - t0
            return clips, dur

        for slot in comp['slots']:
            sid = slot['id']
            lo, hi = slot.get('duration', [3, 8])
            target = (lo + hi) / 2
            if slot.get('type') == 'end_card':
                plan['slots'][sid] = {'headline': brief.get('end_text', ''), 'bullets': brief.get('bullets', msgs[:3]),
                                      'cta': brief.get('cta', 'Shop now'), 'image_seg': demo[0] if demo else None}
                total += 3.5
            elif slot['audio'][0] == 'speaker' and lead:
                who = lead if sid in ('hook', 'testimonial', 'testimonial_1') or not others else others[(len(plan['slots'])) % len(others)]
                clips, d = speak(who, min(target, hi), cap=hi if sid == 'hook' else 8.0, rotate=n if sid == 'hook' else 0, max_clips=1 if sid == 'hook' else 99)
                for o in (others if sid != 'hook' else []):   # compléter avec d'autres personnes si la case est trop courte
                    if d >= lo:
                        break
                    more, d2 = speak(o, lo - d + 2)
                    clips += more; d += d2
                plan['slots'][sid] = {'clips': clips}
                total += d
            elif sid == 'story' and lead:   # témoignage illustré : la voix du client sous les plans
                lines, d = [], 0.0
                for k in sorted(speakers[lead], key=lambda k: segs[k]['start']):
                    if d >= target or k in used:
                        continue
                    s = segs[k]
                    r = _cut(files[s['file']], s, 8.0)
                    if not r or r[1] - r[0] < 1.5:
                        continue
                    t0, t1, text = r
                    wav = out / 'audio' / f"{x['id']}_{k}.wav"
                    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t0), '-to', str(t1), '-i',
                                    files[s['file']]['path'], '-vn', '-ac', '2', '-ar', '48000', str(wav)], check=True)
                    need = (t1 - t0) + 0.4
                    clips, have = [], 0.0
                    while have < need:
                        c = take_demo(1)
                        if not c:
                            break
                        clips += c
                        have += segs[c[0]['seg']]['dur']
                    if have < need:
                        break   # plus assez de plans pour illustrer cette phrase
                    used.add(k)
                    lines.append({'text': text, 'audio': str(wav.resolve()), 'clips': clips})
                    d += t1 - t0
                plan['slots'][sid] = {'audio': 'voiceover', 'lines': lines}
                total += d
            else:   # voix off sur plans de démo
                lines, d = [], 0.0
                while d < target and msgs:
                    text = msgs[m_ptr % len(msgs)]
                    need = max(1.8, len(text.split()) / 2.6) + 0.6
                    clips, have = [], 0.0
                    while have < need:
                        c = take_demo(1)
                        if not c:
                            break
                        clips += c
                        have += segs[c[0]['seg']]['dur']
                    if have < need:
                        break   # plus assez de plans de démo libres
                    m_ptr += 1
                    lines.append({'text': text, 'clips': clips})
                    d += need - 0.6
                    if len(lines) >= 4:
                        break
                plan['slots'][sid] = {'audio': 'voiceover', 'lines': lines}
                total += d
        plan['estimated_duration'] = f'{round(total)} s'
        (out / f"{x['name']}.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"{len(v['variants'])} plans (premier jet) → {out}")


# ---------- nom final ----------

def final_names(a):
    """Nom final : MM.JJ.AA_<produit>_<identifiant>_Videoask_V<x>, x = dernière version + 1."""
    import re
    v = load(a.variants)
    existing = []
    if a.existing:
        lst = load(a.existing)
        lst = lst.get('entries', lst) if isinstance(lst, dict) else lst
        existing = [e['name'] if isinstance(e, dict) else str(e) for e in lst]
    base = f"{a.date}_{a.product}_{a.ident}_Videoask_V"
    last = 0
    for n in existing:
        m = re.search(r'_Videoask_V(\d+)', n, re.I)
        if m and n.lower().startswith(f"{a.date}_{a.product}_{a.ident}".lower()):
            last = max(last, int(m.group(1)))
    only = [o for o in (a.only or '').split(',') if o]
    k = last
    for x in v['variants']:
        if only and x['id'] not in only:
            continue
        k += 1
        x['final_name'] = f'{base}{k}'
        print(f"{x['id']} → {x['final_name']}.mp4")
    Path(a.variants).write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    m = sub.add_parser('matrix')
    m.add_argument('index')
    m.add_argument('--n', type=int, default=10)
    m.add_argument('--style', default='auto')
    m.add_argument('--composition', default='auto')
    m.add_argument('--must', default='')
    m.add_argument('--project', default='video')
    m.add_argument('--out', default='variants.json')
    b = sub.add_parser('board')
    b.add_argument('variants')
    b.add_argument('--plans')
    d = sub.add_parser('draft')
    d.add_argument('variants')
    d.add_argument('brief')
    d.add_argument('--out', default='plans')
    f = sub.add_parser('names')
    f.add_argument('variants')
    f.add_argument('--date', required=True)
    f.add_argument('--product', required=True)
    f.add_argument('--ident', required=True)
    f.add_argument('--existing', help='listing JSON du dossier SORTIES (device_list_dir)')
    f.add_argument('--only')
    u = sub.add_parser('build')
    u.add_argument('plans')
    u.add_argument('--final', action='store_true')
    u.add_argument('--only')
    u.add_argument('--out')
    a = ap.parse_args()
    sys.exit({'matrix': matrix, 'board': board, 'draft': draft, 'names': final_names, 'build': build}[a.cmd](a) or 0)


if __name__ == '__main__':
    main()
