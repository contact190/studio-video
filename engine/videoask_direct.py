#!/usr/bin/env python3
"""VideoAsk en direct (sans Drive) : liste les réponses vidéo d'une videoask et les télécharge.

Entrée : la réponse de l'API VideoAsk (GET /forms/<form_id>/contacts?include_answers=true), obtenue par
le connecteur Make (module VideoAsk « Make an API Call », connexion de l'utilisateur), enregistrée en JSON.
Facultatif : les questions (GET /forms/<form_id>/questions) pour numéroter Q01, Q02…

  python3 engine/videoask_direct.py list contacts.json [--questions questions.json] [--since 2026-11-01]
      → tableau numéroté (n°, personne, date, question, durée, début de la transcription) + answers.json
  python3 engine/videoask_direct.py fetch answers.json --only 1,4,7 --out <dossier>
      → télécharge les vidéos choisies sous le même nom que le script Drive (Nom_AAAA-MM-JJ_HHmm_Qnn.mp4).
        Le dossier s'indexe ensuite comme n'importe quel dossier (Analyse).
Le téléchargement direct demande que le domaine des médias VideoAsk soit autorisé (Settings ›
Capabilities) ; sinon, l'erreur le dit et on passe par le Drive comme avant.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def load(p):
    d = json.load(open(p, encoding='utf-8'))
    for k in ('body', 'data', 'results', 'items'):
        if isinstance(d, dict) and k in d:
            d = d[k]
    return d if isinstance(d, list) else [d]


def slug(name):
    s = re.sub(r'[^A-Za-zÀ-ÿ0-9 \-]', '', str(name or 'Anonyme')).strip()
    parts = s.split()
    return (parts[0] + ('_' + parts[1][0].upper() if len(parts) > 1 else '')) if parts else 'Anonyme'


def list_cmd(a):
    qidx = {}
    if a.questions:
        qs = load(a.questions)
        qs = sorted(qs, key=lambda q: q.get('order', q.get('position', 0)))
        qidx = {q.get('question_id', q.get('id')): (i + 1, q.get('label') or q.get('title') or '') for i, q in enumerate(qs)}
    rows = []
    for c in load(a.contacts):
        who = slug(c.get('name'))
        for ans in c.get('answers', []) or []:
            url = ans.get('media_url') or ans.get('share_url')
            if ans.get('type') not in (None, 'video') or not url:
                continue
            when = str(ans.get('created_at') or c.get('created_at') or '')[:16]
            if a.since and when[:10] < a.since:
                continue
            qn, qlabel = qidx.get(ans.get('question_id'), (len([r for r in rows if r['who'] == who]) + 1, ''))
            stamp = when.replace('T', '_').replace(':', '')
            rows.append({'who': who, 'when': when, 'q': qn, 'question': qlabel,
                         'duration': ans.get('media_duration'), 'url': url,
                         'text': (ans.get('transcription') or '').strip(),
                         'name': f"{who}_{stamp}_Q{qn:02d}.mp4"})
    rows.sort(key=lambda r: r['when'], reverse=True)
    for i, r in enumerate(rows, 1):
        r['n'] = i
    json.dump(rows, open('answers.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('| n° | Personne | Date | Question | Durée | Ce qu\'elle dit |')
    print('|---|---|---|---|---|---|')
    for r in rows:
        d = f"{r['duration']:.0f} s" if isinstance(r['duration'], (int, float)) else '—'
        print(f"| {r['n']} | {r['who']} | {r['when'].replace('T', ' ')} | Q{r['q']:02d} {r['question'][:30]} | {d} | {r['text'][:70]} |")
    print(f"\n{len(rows)} réponses vidéo → answers.json")


def fetch_cmd(a):
    rows = json.load(open(a.answers, encoding='utf-8'))
    want = {int(x) for x in a.only.split(',')} if a.only else {r['n'] for r in rows}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ok = 0
    for r in rows:
        if r['n'] not in want:
            continue
        dest = out / r['name']
        if dest.exists() and dest.stat().st_size > 0:
            ok += 1
            continue
        res = subprocess.run(['curl', '-sSfL', '--max-time', '300', '-o', str(dest), r['url']], capture_output=True, text=True)
        if res.returncode != 0:
            dest.unlink(missing_ok=True)
            host = re.sub(r'^https?://([^/]+).*', r'\1', r['url'])
            sys.exit(f"Téléchargement refusé pour {host} : autoriser ce domaine dans Settings › Capabilities, "
                     f"ou passer par le Drive. ({res.stderr.strip()[:120]})")
        ok += 1
    print(f'{ok} vidéos dans {out}')


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    l = sub.add_parser('list'); l.add_argument('contacts'); l.add_argument('--questions'); l.add_argument('--since')
    f = sub.add_parser('fetch'); f.add_argument('answers'); f.add_argument('--only'); f.add_argument('--out', required=True)
    a = ap.parse_args()
    {'list': list_cmd, 'fetch': fetch_cmd}[a.cmd](a)


if __name__ == '__main__':
    main()
