#!/usr/bin/env python3
"""Classe les pubs Meta d'une période et propose quoi décliner.

Entrée : le JSON renvoyé par le connecteur Meta (ads_get_ad_entities, level=ad), tel quel
ou sa liste `ad_entities`. Champs utilisés (ceux qui manquent sont ignorés) :
  id, name, campaign_name, creative_id, effective_status, amount_spent, impressions, ctr,
  results, cost_per_result, video_play_actions, video_continuous_2_sec_watched_actions,
  video_thruplay_watched_actions, video_p75_watched_actions, video_avg_time_watched_actions

Usage :
  python3 engine/meta_rank.py ads.json [--min-spend 0] [--min-impr 1000] [--out rank.json]
Affiche un tableau numéroté (rang, pub, dépense, résultats, coût/résultat, accroche,
rétention, CTR, score, recommandation) et écrit rank.json pour la suite.

Indicateurs :
  accroche  = lectures de 2 s continues / impressions    (part des gens qui s'arrêtent)
  rétention = lectures complètes (ThruPlay) / lectures 2 s (part de ceux qui restent)
Score sur 100 entre pubs comparables : coût par résultat 40 %, accroche 25 %, rétention 20 %,
CTR 15 % (rangs centiles ; sans résultats, le coût est remplacé par le CTR).
"""
import argparse
import json
import sys


def num(v):
    if v is None:
        return None
    if isinstance(v, dict):
        for k in ('value', 'amount', 'values'):
            if k in v:
                return num(v[k])
        return None
    if isinstance(v, list):
        vals = [num(x) for x in v]
        vals = [x for x in vals if x is not None]
        return vals[0] if vals else None
    try:
        return float(str(v).replace(',', '').replace('%', '').split()[0])
    except (ValueError, IndexError):
        return None


def load(path):
    d = json.load(open(path, encoding='utf-8'))
    if isinstance(d, dict):
        d = d.get('ad_entities', d.get('data', []))
    if isinstance(d, str):
        d = json.loads(d)
    return d


def pct_rank(vals, v, higher_better=True):
    vs = sorted(x for x in vals if x is not None)
    if v is None or not vs:
        return 0.5
    below = sum(1 for x in vs if x < v)
    eq = sum(1 for x in vs if x == v)
    r = (below + 0.5 * eq) / len(vs)
    return r if higher_better else 1 - r


def recommend(a, med):
    if a['eligible'] is False:
        return 'Trop peu de données pour juger'
    hook_ok = a['hook'] is not None and med['hook'] is not None and a['hook'] >= med['hook']
    hold_ok = a['hold'] is not None and med['hold'] is not None and a['hold'] >= med['hold']
    cheap = a['cpr'] is not None and med['cpr'] is not None and a['cpr'] <= med['cpr']
    if a['score'] >= 70 or (a.get('top') and a['score'] >= 55):
        return 'Gagnante : à décliner en priorité (garder la structure, varier accroche et personne)'
    if hook_ok and not hold_ok:
        return "Bonne accroche mais on décroche : garder l'accroche, retravailler la suite"
    if hold_ok and not hook_ok:
        return 'Retient bien mais accroche faible : tester de nouvelles accroches'
    if cheap:
        return 'Résultats bon marché : décliner en gardant le message'
    if a['score'] < 35:
        return 'À ne pas décliner'
    return 'Moyenne : à décliner seulement pour tester une idée'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ads')
    ap.add_argument('--min-spend', type=float, default=None, help='dépense minimale (défaut : 20 %% de la médiane)')
    ap.add_argument('--min-impr', type=float, default=1000)
    ap.add_argument('--out', default='rank.json')
    a = ap.parse_args()

    rows = []
    for e in load(a.ads):
        imp = num(e.get('impressions')) or 0
        p2 = num(e.get('video_continuous_2_sec_watched_actions'))
        thru = num(e.get('video_thruplay_watched_actions'))
        rows.append({
            'ad_id': str(e.get('id')), 'name': e.get('name', ''), 'campaign': e.get('campaign_name', ''),
            'creative_id': str(e.get('creative_id') or ''), 'status': e.get('effective_status', ''),
            'spend': num(e.get('amount_spent')) or 0, 'impressions': imp, 'ctr': num(e.get('ctr')),
            'results': num(e.get('results')), 'cpr': num(e.get('cost_per_result')),
            'hook': (p2 / imp) if (p2 is not None and imp) else None,
            'hold': (thru / p2) if (thru is not None and p2) else None,
            'avg_watch': num(e.get('video_avg_time_watched_actions')),
            'is_video': bool(num(e.get('video_play_actions'))),
        })
    if not rows:
        sys.exit('Aucune pub sur cette période.')
    spends = sorted(r['spend'] for r in rows)
    med_spend = spends[len(spends) // 2]
    min_spend = a.min_spend if a.min_spend is not None else 0.2 * med_spend
    for r in rows:
        r['eligible'] = r['spend'] >= min_spend and r['impressions'] >= a.min_impr
        if r['cpr'] is not None and not r['results']:
            r['cpr'] = None
    el = [r for r in rows if r['eligible']] or rows
    use_cpr = sum(1 for r in el if r['cpr'] is not None) >= 2

    def med(k):
        vs = sorted(r[k] for r in el if r[k] is not None)
        return vs[len(vs) // 2] if vs else None
    meds = {k: med(k) for k in ('hook', 'hold', 'cpr', 'ctr')}
    for r in rows:
        parts = [(0.25, pct_rank([x['hook'] for x in el], r['hook'])),
                 (0.20, pct_rank([x['hold'] for x in el], r['hold'])),
                 (0.15 if use_cpr else 0.55, pct_rank([x['ctr'] for x in el], r['ctr']))]
        if use_cpr:
            parts.append((0.40, pct_rank([x['cpr'] for x in el], r['cpr'], higher_better=False)))
        r['score'] = round(100 * sum(w * v for w, v in parts) / sum(w for w, _ in parts))
        if not r['eligible']:
            r['score'] = min(r['score'], 40)
    rows.sort(key=lambda r: (r['eligible'], r['score']), reverse=True)
    for i, r in enumerate(rows, 1):
        r['rank'] = i
        r['top'] = i == 1 and r['eligible']
        r['recommendation'] = recommend(r, meds)

    f = lambda v, p=0, s='': '—' if v is None else f'{v:,.{p}f}{s}'.replace(',', ' ')
    print('| # | Pub | Dépense | Résultats | Coût/résultat | Accroche | Rétention | CTR | Score | Recommandation |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    for r in rows:
        print(f"| {r['rank']} | {r['name'][:40]} | {f(r['spend'])} | {f(r['results'])} | {f(r['cpr'])} | "
              f"{f(None if r['hook'] is None else 100 * r['hook'], 0, ' %')} | {f(None if r['hold'] is None else 100 * r['hold'], 0, ' %')} | "
              f"{f(r['ctr'], 2, ' %')} | {r['score']} | {r['recommendation']} |")
    json.dump({'min_spend': min_spend, 'medians': meds, 'ads': rows}, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"\n{sum(r['eligible'] for r in rows)} pubs comparables sur {len(rows)} (dépense ≥ {f(min_spend)}, ≥ {int(a.min_impr)} impressions).")


if __name__ == '__main__':
    main()
