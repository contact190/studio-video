"""Monte une vidéo à partir d'un plan de montage (écrit par Claude), d'un style et d'une composition.

Usage : python3 engine/build.py <plan.json> [--out <dossier>] [--preview]
  --preview : rendu en demi-résolution, plus rapide, pour vérifier avant le rendu final

Le plan (voir docs/plan.md) dit, case par case, quels segments de rushes utiliser :
- cases « speaker »   : la personne filmée parle, ses mots deviennent les sous-titres ;
- cases « voiceover » : des lignes de texte lues par la voix off, illustrées par des segments.
"""
import argparse, json, re, shutil, sys, wave
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, FPS, FORMATS, run, probe, load_json, save_json, library, fmt_t

RENDER = ROOT / 'render'
PUNCT = '.,!?;:'


class PlanError(Exception):
    pass


# ---------------------------------------------------------------- utilitaires
def resolve(obj, brand):
    """Remplace les valeurs « brand.xxx » d'un style par celles de la marque."""
    if isinstance(obj, dict):
        return {k: resolve(v, brand) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve(v, brand) for v in obj]
    if isinstance(obj, str) and obj.startswith('brand.'):
        return brand.get(obj[6:], obj)
    return obj


def wav_dur(p):
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def spread_words(text, t0, t1):
    ws = text.split()
    if not ws:
        return []
    weight = [len(w) + 1.5 + (2.5 if w[-1] in '.!?' else 1.2 if w[-1] in ',;:' else 0) for w in ws]
    tot, acc, out = sum(weight), 0.0, []
    for w, k in zip(ws, weight):
        a = t0 + (t1 - t0) * acc / tot
        acc += k
        out.append((w, a, t0 + (t1 - t0) * acc / tot))
    return out


def fair_split(need, avail, min_shot=0.6):
    """Partage la durée d'une ligne entre ses plans : parts égales, sans dépasser ce que chaque plan offre."""
    n = len(avail)
    share = [0.0] * n
    left, open_ = need, list(range(n))
    while open_ and left > 1e-6:
        part = left / len(open_)
        done = [i for i in open_ if avail[i] - share[i] <= part]
        if not done:
            for i in open_: share[i] += part
            left = 0; break
        for i in done:
            left -= avail[i] - share[i]; share[i] = avail[i]; open_.remove(i)
    # un plan trop court est fusionné dans le précédent
    for i in range(n):
        if 0 < share[i] < min_shot and n > 1:
            j = i - 1 if i > 0 else i + 1
            room = avail[j] - share[j]
            take = min(room, share[i])
            share[j] += take; share[i] -= take
    return share


KEYWORDS = set()

_UNITS = {w: i for i, w in enumerate('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split())}
_TENS = {w: 10 * i for i, w in enumerate('_ _ twenty thirty forty fifty sixty seventy eighty ninety'.split()) if w != '_'}


def find_number(text):
    """Premier nombre d'une phrase, en chiffres ou en lettres : (valeur, suffixe, suite du texte)."""
    import re
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*(%|x|×|k|\+)?', text)
    if m:
        return float(m.group(1).replace(',', '.')), m.group(2) or '', text[m.end():]
    words = re.findall(r"[A-Za-z]+|[^A-Za-z]+", text)
    toks = [w.lower() for w in words]
    for i, w in enumerate(toks):
        if w in _UNITS or w in _TENS or w == 'hundred':
            val, j = 0, i
            while j < len(toks):
                t = toks[j]
                if t in _TENS: val += _TENS[t]
                elif t in _UNITS: val += _UNITS[t]
                elif t == 'hundred': val = max(val, 1) * 100
                elif t.strip() in ('-', '') and j + 1 < len(toks) and (toks[j + 1] in _UNITS or toks[j + 1] in _TENS): pass
                else: break
                j += 1
            if val < 2 and toks[i] in ('one', 'zero'):
                continue
            rest = ''.join(words[j:])
            suf = ''
            if re.match(r'\s*percent', rest, re.I):
                suf = '%'; rest = re.sub(r'^\s*percent', '', rest, flags=re.I)
            return float(val), suf, rest
    return None



def _norm(w):
    return ''.join(ch for ch in w.lower() if ch.isalnum() or ch == '%')


def chunk_words(words, style, slot_end):
    st = style['subtitles']
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        chars = sum(len(x[0]) + 1 for x in cur)
        if len(cur) >= st['max_words'] or chars >= st['max_chars'] or w[0][-1] in PUNCT:
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    out = []
    for i, c in enumerate(chunks):
        start = c[0][1]
        nxt = chunks[i + 1][0][1] if i + 1 < len(chunks) else None
        end = nxt if nxt is not None and nxt - c[-1][2] < 0.6 else c[-1][2] + 0.25
        end = min(end, slot_end)
        if end - start < 0.12:
            continue
        hi = len(c) - 1 if (st.get('highlight') == 'last_word_every_other' and i % 2 == 1) or st.get('highlight') == 'last_word' else -1
        if st.get('highlight') == 'keywords':   # mots clés du brief
            kw = [j for j, x in enumerate(c) if _norm(x[0]) in KEYWORDS]
            hi = kw[0] if kw else -1
        elif st.get('highlight') == 'word':
            hi = len(c) - 1
        out.append({'t0': start, 't1': end, 'words': [x[0].strip() for x in c], 'hi': hi})
    return out


# ---------------------------------------------------------------- préparation des plans
def prep_clip(src, t_in, dur, out, W, H, fx=0.5, fy=0.5, has_audio=True, half=False):
    n = max(1, round(dur * FPS))
    if half:
        W, H = W // 2, H // 2
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H}:(iw-{W})*{fx}:(ih-{H})*{fy},fps={FPS},setsar=1,format=yuv420p")
    cmd = ['ffmpeg', '-v', 'error', '-y', '-ss', f'{t_in:.3f}', '-i', str(src)]
    if not has_audio:
        cmd += ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo']
    cmd += ['-vf', vf, '-frames:v', str(n), '-map', '0:v', '-map', '0:a' if has_audio else '1:a',
            '-af', f'afade=t=in:d=0.03,afade=t=out:st={max(0, n / FPS - 0.05):.3f}:d=0.05',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-c:a', 'aac', '-ar', '48000', '-ac', '2',
            '-t', f'{n / FPS:.3f}', str(out)]
    run(cmd)
    return n


def still(src, t, out, W):
    run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.2f}', '-i', str(src), '-frames:v', '1', '-vf', f'scale={W}:-2', str(out)])


# ---------------------------------------------------------------- construction
def build(plan_path, out_dir=None, preview=False):
    plan = load_json(plan_path)
    KEYWORDS.clear(); KEYWORDS.update(_norm(w) for w in plan.get('keywords', []))
    style_raw = library('styles', plan['style'])
    comp = library('compositions', plan['composition'])
    brand = library('brand', plan.get('brand', 'neutre'))
    style = resolve(style_raw, brand)
    idx = load_json(plan['rushes_index'])
    if not idx:
        raise PlanError(f"Index de rushes introuvable : {plan['rushes_index']}")
    W, H = FORMATS[plan.get('format', '9:16')]
    title = re.sub(r'[^a-zA-Z0-9_-]+', '-', plan.get('title', 'video')).strip('-') or 'video'
    out_dir = Path(out_dir or Path(plan_path).parent / 'output')
    out_dir.mkdir(parents=True, exist_ok=True)
    media = RENDER / 'public' / 'media'
    shutil.rmtree(media, ignore_errors=True); media.mkdir(parents=True)

    errors, warns = [], []
    used = {}
    T = 0.0                       # curseur temps (s)
    clips, voice, subs, tags, duck, report = [], [], [], [], [], []
    hook = end = None
    slot_marks = []

    def seg_of(c, slot):
        s = idx['segments'].get(c['seg'])
        if not s:
            errors.append(f"[{slot}] segment inconnu : {c['seg']}"); return None
        if not s.get('usable', True) and not c.get('force'):
            errors.append(f"[{slot}] {c['seg']} est marqué inutilisable ({', '.join(s['issues']) or s.get('description', '')})")
        if c['seg'] in used and not c.get('allow_repeat'):
            errors.append(f"[{slot}] {c['seg']} déjà utilisé dans « {used[c['seg']]} » (pas de plan répété)")
        used[c['seg']] = slot
        return s

    def src_path(f):
        if plan.get('rushes_dir') and f.get('rel'):
            p = Path(plan['rushes_dir']) / f['rel']
            if p.exists():
                return p
        if Path(f['path']).exists():
            return Path(f['path'])
        raise PlanError(f"Rush introuvable : {f.get('rel', f['name'])} (à rapatrier avant le montage)")

    def add_clip(s, c, t_in, dur, volume, slot):
        f = idx['files'][s['file']]
        k = len(clips) + 1
        name = f'c{k:02d}.mp4'
        r = s.get('rea') or {}
        fx = c.get('focus_x', r.get('center_x') if r.get('center_x') is not None else 0.5)
        fy = c.get('focus_y', 0.5)
        n = prep_clip(src_path(f), t_in, dur, media / name, W, H, min(1, max(0, fx)), fy, f['has_audio'], preview)
        frm = round(T * FPS)
        clips.append({'src': f'media/{name}', 'from': frm, 'dur': n, 'volume': volume, 'seed': k, 'speaker': volume > 0})
        if c.get('tag'):
            label, _, txt = c['tag'].rpartition('|')
            tags.append({'from': frm, 'to': frm + n, 'text': txt.strip(), 'label': label.strip()})
        report.append({'slot': slot, 'segment': s['id'], 'file': f['name'], 'in': round(t_in, 2), 'out': round(t_in + dur, 2),
                       'at': round(T, 2), 'description': s.get('description', '')})
        return n / FPS

    overlays, last_who = [], [None]
    reviews = plan.get('reviews', [])
    for slot in comp['slots']:
        sid = slot['id']
        p = plan['slots'].get(sid)
        if p is None:
            errors.append(f"Case « {sid} » ({slot['role']}) absente du plan"); continue
        start = T
        if slot.get('type') == 'end_card':
            d = style['end_card']['duration']
            img = None
            if p.get('image_seg') and p['image_seg'] in idx['segments']:
                s = idx['segments'][p['image_seg']]
                still(src_path(idx['files'][s['file']]), (s['start'] + s['end']) / 2, media / 'end.jpg', W // (2 if preview else 1))
                img = 'media/end.jpg'
            end = {'from': round(T * FPS), 'dur': round(d * FPS), 'headline': p.get('headline', ''), 'bullets': p.get('bullets', []),
                   'cta': p.get('cta', brand.get('cta', '')), 'image': img, 'logo_text': brand.get('logo_text', ''), 'website': brand.get('website', '')}
            T += round(d * FPS) / FPS
        elif p.get('audio', slot['audio'][0]) == 'speaker':
            for c in p.get('clips', []):
                s = seg_of(c, sid)
                if not s: continue
                import re as _re
                fname = idx['files'][s['file']]['name']
                who = (s.get('person') or (fname.split('_')[0] if _re.match(r'^[A-Za-zÀ-ÿ\- ]+_.*\d{4}-\d{2}-\d{2}', fname) else None))
                if style.get('lower_third') and who and who != last_who[0] and sid != 'hook':
                    overlays.append({'type': 'name', 'text': who, 'sub': style.get('lower_third_sub', 'Verified customer'),
                                     'from': round(T * FPS), 'to': round(T * FPS) + 75})
                last_who[0] = who
                t_in = c.get('in', s['start']); t_out = c.get('out', s['end'])
                f = idx['files'][s['file']]
                if t_out <= t_in or t_out > f['duration'] + 0.05:
                    errors.append(f"[{sid}] {c['seg']} : entrée/sortie invalides ({t_in}–{t_out})"); continue
                clip_start = T
                d = add_clip(s, c, t_in, t_out - t_in, 1.0, sid)
                if c.get('subtitle'):
                    sp = [x for x in f['speech'] if x['end'] > t_in and x['start'] < t_out]
                    a = max(t_in, sp[0]['start']) if sp else t_in
                    z = min(t_out, sp[-1]['end']) if sp else t_out
                    ws = spread_words(c['subtitle'], clip_start + a - t_in, clip_start + z - t_in)
                else:
                    ws = [(w, clip_start + w0 - t_in, clip_start + w1 - t_in) for sp in f['speech'] for w, w0, w1 in sp.get('words', [])
                          if t_in <= (w0 + w1) / 2 < t_out]
                subs += chunk_words(ws, style, clip_start + d)
                duck.append([round(clip_start * FPS), round((clip_start + d) * FPS)])
                T += d
        else:   # voix off
            from tts import synth
            vcfg = plan.get('voice', {})
            for li, line in enumerate(p.get('lines', [])):
                wav = media / f'vo_{sid}_{li + 1}.wav'
                if line.get('audio'):
                    run(['ffmpeg', '-v', 'error', '-y', '-i', line['audio'], '-ar', '48000', str(wav)])
                    vd = wav_dur(wav)
                else:
                    try:
                        vd = synth(line['text'], wav, vcfg.get('voice', 'am_michael'), vcfg.get('speed', 1.05))
                    except ValueError as e:
                        errors.append(f"[{sid}] ligne {li + 1} : {e}"); continue
                need = vd + line.get('gap', 0.15)
                segs = [(c, seg_of(c, sid)) for c in line.get('clips', [])]
                segs = [(c, s) for c, s in segs if s]
                if not segs:
                    errors.append(f"[{sid}] ligne {li + 1} : aucun plan pour l'illustrer"); continue
                avail = [c.get('out', s['end']) - c.get('in', s['start']) for c, s in segs]
                if sum(avail) < need - 0.05:
                    errors.append(f"[{sid}] ligne {li + 1} « {line['text'][:40]} » dure {need:.1f}s mais ses plans n'offrent que {sum(avail):.1f}s : ajoute un plan")
                    continue
                share = fair_split(need, avail)
                line_start = T
                voice.append({'src': f'media/{wav.name}', 'from': round(T * FPS), 'volume': style['voiceover']['volume']})
                for (c, s), d in zip(segs, share):
                    if d < 0.2:
                        continue
                    t_in = c.get('in', s['start'] + 0.1 if s['dur'] > d + 0.3 else s['start'])
                    T += add_clip(s, c, t_in, d, c.get('volume', 0.0), sid)
                if slot.get('stats'):
                    import re as _re
                    st_ = find_number(line['text'])
                    if st_:
                        val, suf, rest = st_
                        overlays.append({'type': 'stat', 'value': val, 'suffix': suf,
                                         'label': line.get('stat_label') or ' '.join(rest.split()[:3]).strip(' .,:;'),
                                         'from': round(line_start * FPS), 'to': round(T * FPS)})
                subs += chunk_words(spread_words(line['text'], line_start, line_start + vd), style, T)
                duck.append([round(line_start * FPS), round((line_start + vd) * FPS)])
        dur = T - start
        lo, hi = slot.get('duration', [0, 1e9])
        if dur and not (lo - 0.3 <= dur <= hi + 0.3):
            warns.append(f"Case « {sid} » : {dur:.1f}s (attendu {lo}–{hi}s)")
        slot_marks.append({'slot': sid, 'from': round(start * FPS), 'to': round(T * FPS)})
        card = (p or {}).get('card') or (slot.get('card') if slot.get('card') != 'question' else None)
        if card and T > start:
            overlays.append({'type': 'card', 'text': card, 'from': round(start * FPS), 'to': round(start * FPS) + min(36, round((T - start) * FPS))})
        if style.get('review_cards') and slot.get('audio', [''])[0] == 'speaker' and sid != 'hook' and T - start > 2 and reviews:
            overlays.append({'type': 'review', 'text': reviews[len([o for o in overlays if o['type'] == 'review']) % len(reviews)],
                             'from': round(start * FPS) + 9, 'to': round(min(T, start + 3.5) * FPS)})

    if p_hook := plan.get('hook_title'):
        if style['hook_title']['enabled']:
            hook = {'text': p_hook, 'from': 0, 'to': round(min(style['hook_title']['duration'], T) * FPS)}
    total = round(T * FPS)
    lo, hi = comp.get('target_duration', [0, 1e9])
    if not lo <= T <= hi:
        warns.append(f"Durée totale {T:.1f}s hors de la cible {lo}–{hi}s")
    if errors:
        raise PlanError('\n'.join(errors))

    # musique
    music = None
    mcfg = plan.get('music', 'auto')
    if mcfg != 'none':
        mfile = media / 'music.wav'
        if isinstance(mcfg, dict) and mcfg.get('file'):
            run(['ffmpeg', '-v', 'error', '-y', '-i', mcfg['file'], '-t', f'{T + 0.5:.2f}', '-ar', '48000', '-ac', '2', str(mfile)])
        else:
            from music import make
            calm = [(m['from'] / FPS, m['to'] / FPS) for m in slot_marks if m['slot'] not in ('hook', 'end')]
            make(mfile, T + 0.4, calm=calm, hits=[0.0] + ([end['from'] / FPS] if end else []))
        music = {'src': 'media/music.wav', 'volume': style['music']['volume'], 'duck_to': style['music']['duck_to'], 'ranges': duck}

    if style.get('sfx') == 'whoosh' and len(slot_marks) > 1:
        wh = media / 'whoosh.wav'
        run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anoisesrc=d=0.4:c=pink:a=0.6', '-af',
             'highpass=f=400,lowpass=f=6000,afade=t=in:d=0.18,afade=t=out:st=0.2:d=0.2,aformat=channel_layouts=stereo', '-ar', '48000', str(wh)])
        for m in slot_marks[1:]:
            voice.append({'src': 'media/whoosh.wav', 'from': max(0, m['from'] - 5), 'volume': 0.35})
    broll = None
    if (style.get('image') or {}).get('layout') == 'split':
        demo_c = next((c for c in clips if not c['speaker']), None)
        if demo_c:
            broll = {'src': demo_c['src'], 'dur': demo_c['dur']}
    if preview:
        W, H = W // 2, H // 2
    timeline = {'overlays': overlays, 'broll': broll, 'width': W, 'height': H, 'fps': FPS, 'durationInFrames': total, 'style': style, 'brand': brand,
                'clips': clips, 'voice': voice, 'music': music, 'subtitles': [{**s, 'from': round(s['t0'] * FPS), 'to': round(s['t1'] * FPS)} for s in subs],
                'tags': tags, 'hook': hook, 'end': end, 'slots': slot_marks}
    props = RENDER / 'props.json'
    save_json(props, timeline)

    raw = out_dir / f'{title}.raw.mp4'
    final = out_dir / f'{title}{"_preview" if preview else ""}.mp4'
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    cmd = ['npx', 'remotion', 'render', 'src/index.jsx', 'Edit', str(raw), f'--props={props}', '--codec=h264', '--crf=18',
           '--concurrency=2', '--log=error']
    if chrome:
        cmd += [f'--browser-executable={chrome}', '--chrome-mode=chrome-for-testing']
    run(cmd, cwd=RENDER)
    tmp = final.with_suffix('.tmp.mp4')
    run(['ffmpeg', '-v', 'error', '-y', '-i', str(raw), '-c:v', 'copy', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=9', '-ar', '48000',
         '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(tmp)])
    tmp.replace(final); raw.unlink(missing_ok=True)

    # journal « case → plan utilisé » + mémoire des segments utilisés
    save_json(out_dir / f'{title}.report.json', {'video': str(final), 'duration': round(T, 2), 'warnings': warns, 'edit': report,
                                                  'style': f"{style_raw['id']} v{style_raw['version']}", 'composition': f"{comp['id']} v{comp['version']}"})
    if not preview:
        for r in report:
            s = idx['segments'][r['segment']]
            if title not in s['used_in']:
                s['used_in'].append(title)
        save_json(plan['rushes_index'], idx)
    print(f'Vidéo : {final}  ({T:.1f}s, {len(clips)} plans)')
    for w in warns:
        print('  attention :', w)
    for r in report:
        print(f"  {r['slot']:<12} {fmt_t(r['at'])}  {r['segment']}  {r['file']} {fmt_t(r['in'])}-{fmt_t(r['out'])}")
    return final


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('plan'); ap.add_argument('--out'); ap.add_argument('--preview', action='store_true')
    a = ap.parse_args()
    try:
        build(a.plan, a.out, a.preview)
    except PlanError as e:
        print('Le plan doit être corrigé :\n' + str(e)); sys.exit(2)
