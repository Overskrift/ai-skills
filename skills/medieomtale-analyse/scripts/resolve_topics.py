#!/usr/bin/env python3
"""
resolve_topics.py: Validerer agentens topics.json og beregner alt det
mekaniske omkring mærkesagerne, så HTML og PPTX viser præcis de samme tal.

Brug:
    python3 resolve_topics.py <metrics.json> <substantive.json> <topics.json> \
        --out <topics_resolved.json>

topics.json (skrevet af agenten i trin 2), foretrukket format:
    {"topics": [{"title": "...", "desc": "...",
                 "post_idx": [3, 7, 12, ...],      # ALLE omtaler der handler om temaet
                 "example_idx": [7, 12]}]}         # 2 repræsentative, helst fra post_idx

Fallback for meget store datasæt, hvor det ikke er realistisk at klassificere
hver omtale: angiv "count" (et skøn) i stedet for "post_idx". Så markeres
tallene som skøn ("ca.") i rapporten, og summen af skøn må ikke overstige
det samlede antal omtaler.

Hvorfor post_idx: et waffle-diagram forudsætter at kategorierne ikke
overlapper. Omtaler der rammer flere temaer, tælles her kun under det første
(vigtigste) tema, så felterne altid summer til 100 % af alle omtaler.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svg_helpers import PALETTE, apportion_squares  # noqa: E402

REST_GREY = '#d7d9dd'
MAX_TOPICS = 5


def fail(msg):
    print(f'FEJL i topics.json: {msg}', file=sys.stderr)
    sys.exit(2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('metrics')
    ap.add_argument('substantive')
    ap.add_argument('topics')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    with open(args.metrics, encoding='utf-8') as f:
        metrics = json.load(f)
    with open(args.substantive, encoding='utf-8') as f:
        substantive = json.load(f)
    with open(args.topics, encoding='utf-8') as f:
        topics = json.load(f).get('topics')

    total = metrics['total']
    by_idx = {p['idx']: p for p in substantive}

    if not isinstance(topics, list) or not topics:
        fail('"topics" skal være en ikke-tom liste.')
    if len(topics) > MAX_TOPICS:
        fail(f'højst {MAX_TOPICS} temaer, fik {len(topics)}.')
    if len(topics) < MAX_TOPICS:
        print(f'BEMÆRK: {len(topics)} temaer i stedet for {MAX_TOPICS}. OK hvis datasættet er lille.',
              file=sys.stderr)

    uses_idx = all('post_idx' in t for t in topics)
    uses_count = all('count' in t and 'post_idx' not in t for t in topics)
    if not (uses_idx or uses_count):
        fail('brug enten "post_idx" på alle temaer (anbefalet) eller "count" på alle temaer, ikke en blanding.')

    for i, t in enumerate(topics):
        for key in ('title', 'desc'):
            if not str(t.get(key, '')).strip():
                fail(f'tema {i + 1} mangler "{key}".')

    resolved = []
    if uses_idx:
        assigned = set()
        for i, t in enumerate(topics):
            idxs = list(dict.fromkeys(t['post_idx']))
            bad = [x for x in idxs if x not in by_idx]
            if bad:
                fail(f'tema {i + 1} ("{t["title"]}") har post_idx der ikke findes i substantive.json: {bad}')
            primary = [x for x in idxs if x not in assigned]
            assigned.update(primary)
            resolved.append({'t': t, 'count': len(primary), 'touching': len(idxs), 'members': idxs})
        estimated = False
    else:
        for i, t in enumerate(topics):
            c = t['count']
            if not isinstance(c, int) or c < 0:
                fail(f'tema {i + 1} har ugyldigt "count": {c!r}')
            resolved.append({'t': t, 'count': c, 'touching': c, 'members': []})
        s = sum(r['count'] for r in resolved)
        if s > total:
            fail(f'summen af skøn ({s}) er større end antallet af omtaler ({total}). Temaerne overlapper; '
                 f'brug "post_idx", så overlap håndteres korrekt.')
        estimated = True

    counts = [r['count'] for r in resolved]
    rest = max(0, total - sum(counts))
    squares = apportion_squares(counts + [rest], n_squares=100)

    out_topics = []
    for i, r in enumerate(resolved):
        t = r['t']
        ex_idx = t.get('example_idx') or r['members'][:2]
        examples = []
        for x in ex_idx:
            p = by_idx.get(x)
            if p is None:
                print(f'ADVARSEL: example_idx {x} i tema "{t["title"]}" findes ikke; springes over.',
                      file=sys.stderr)
                continue
            if r['members'] and x not in r['members']:
                print(f'ADVARSEL: example_idx {x} er ikke i temaets post_idx ("{t["title"]}").',
                      file=sys.stderr)
            examples.append({'title': p['title'], 'src': p['src'], 'url': p['url'], 'date_da': p['date_da']})
        out_topics.append({
            'title': t['title'].strip(),
            'desc': t['desc'].strip(),
            'color': PALETTE[i % len(PALETTE)],
            'count': r['count'],
            'count_touching': r['touching'],
            'pct': round(100 * r['count'] / total, 1) if total else 0,
            'squares': squares[i],
            'examples': examples,
        })

    result = {
        'estimated': estimated,
        'total': total,
        'topics': out_topics,
        'rest': {
            'title': 'Øvrige omtaler',
            'desc': 'Alt andet i datasættet: enkeltstående nyheder, opslag uden for top 5, sociale medier m.m.',
            'color': REST_GREY,
            'count': rest,
            'pct': round(100 * rest / total, 1) if total else 0,
            'squares': squares[-1],
        },
        'note': ('Tallene er skøn.' if estimated else
                 'Omtaler der berører flere temaer, tælles under det første (vigtigste) tema.'),
    }

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    covered = sum(counts)
    print(f'{args.out} skrevet: {len(out_topics)} temaer dækker {covered} af {total} omtaler '
          f'({"skøn" if estimated else "optalt"}), øvrige={rest}')


if __name__ == '__main__':
    main()
