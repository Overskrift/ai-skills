#!/usr/bin/env python3
"""
compute_metrics.py — Deterministisk beregning af alle metrikker til en
medieomtale-analyse (Overskrift.dk JSON).

Gør ALT det mekaniske arbejde, som ellers ville blive genopfundet i hver
analyse: dedup, KPI'er, tidslinje (med automatisk granularitet), kanal-
fordeling, top-10 kilder, dansk datoformatering, "substantielle" posts til
den kvalitative mærkesags-analyse, samt nyeste/mest markante omtaler.

Det ENESTE trin denne skill stadig kræver LLM-dømmekraft til er "Top 5
mærkesager" (semantisk tema-identifikation) — det gøres IKKE her, men i et
efterfølgende trin hvor Claude læser substantive.json og skriver topics.json.

Brug:
    python3 compute_metrics.py <input.json> --outdir <dir> [--org-name "Navn"]

Output (i --outdir, default: samme mappe som input):
    metrics.json      — alle kvantitative metrikker, klar til rapport-rendering
    substantive.json  — filtrerede posts til den kvalitative temaanalyse
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta

MONTHS_DA = ['januar', 'februar', 'marts', 'april', 'maj', 'juni', 'juli',
             'august', 'september', 'oktober', 'november', 'december']

GK_TRANSLATE = {
    'websites': 'Nyhedssites', 'facebook': 'Facebook', 'linkedin': 'LinkedIn',
    'twitter': 'Twitter/X', 'instagram': 'Instagram', 'youtube': 'YouTube',
    'podcast': 'Podcast', 'blogs': 'Blogs', 'reddit': 'Reddit', 'bluesky': 'Bluesky',
    'trustpilot': 'Trustpilot', 'mastodon': 'Mastodon',
}

DEFAULT_KNOWN_MEDIA = [
    'DR', 'DR Nyheder', 'DR Indland', 'Politiken', 'BT', 'TV 2', 'TV2', 'Berlingske',
    'Jyllands-Posten', 'Ekstra Bladet', 'Finans.dk', 'Børsen', 'Altinget', 'Information',
    'SE og HØR', 'JydskeVestkysten', 'Kristeligt Dagblad', 'Weekendavisen',
]


def clean_text(s):
    """Strip HTML-tags og afkod de mest almindelige entiteter."""
    if not s:
        return ''
    s = re.sub(r'<[^>]+>', ' ', s)
    s = (s.replace('&amp;', '&').replace('&aring;', 'å').replace('&oslash;', 'ø')
           .replace('&aelig;', 'æ').replace('&Aring;', 'Å').replace('&Oslash;', 'Ø')
           .replace('&AElig;', 'Æ').replace('&quot;', '"').replace('&#39;', "'"))
    return re.sub(r'\s+', ' ', s).strip()


def fmt_date_da(iso_date):
    """'YYYY-MM-DD[ ...]' -> 'DD/MM-YYYY' (dansk format, bruges når år indgår)."""
    if not iso_date or len(iso_date) < 10:
        return iso_date or ''
    y, m, d = iso_date[:10].split('-')
    return f"{d}/{m}-{y}"


def fmt_period_da(dt_from, dt_to):
    """Datetime -> 'DD. månedsnavn YYYY' på begge sider af en periode."""
    def one(dt):
        return f"{dt.day}. {MONTHS_DA[dt.month - 1]} {dt.year}"
    return f"{one(dt_from)} – {one(dt_to)}"


def pick_granularity(n_days):
    """Samme regel som SKILL.md's label-format-tabel — nu som kode, ikke prosa."""
    if n_days <= 3:
        return 'hour'
    if n_days <= 60:
        return 'day'
    if n_days <= 186:  # ~6 måneder
        return 'week'
    return 'month'


def is_substantive(p):
    title = clean_text(p.get('item_title') or '').lower()
    desc = clean_text(p.get('item_desc') or '')
    ch = p.get('groupkey', '')
    if re.match(r'^(foto|fotos|video)\s+(fra|af)\b', title):
        return False
    if ch in ('instagram', 'facebook') and len(desc) < 40:
        return False
    if title.startswith('instagram tag') and len(desc) < 5:
        return False
    return True


def is_notable(p, known_media):
    src = (p.get('title') or '').lower()
    return any(k.lower() in src for k in known_media)


def build_timeline(posts):
    dates = [datetime.fromtimestamp(int(p['item_date'])) for p in posts]
    start, end = min(dates).date(), max(dates).date()
    n_days = max(1, (end - start).days + 1)
    gran = pick_granularity(n_days)

    if gran == 'hour':
        buckets = defaultdict(int)
        for d in dates:
            buckets[d.replace(minute=0, second=0, microsecond=0)] += 1
        keys = sorted(buckets)
        labels = [k.strftime('%Hh') for k in keys]
        values = [buckets[k] for k in keys]
        window = 3
    elif gran == 'day':
        buckets = defaultdict(int)
        for d in dates:
            buckets[d.date()] += 1
        keys = []
        cur = start
        while cur <= end:
            keys.append(cur)
            cur += timedelta(days=1)
        labels = [k.strftime('%d/%m') for k in keys]
        values = [buckets.get(k, 0) for k in keys]
        window = 7
    elif gran == 'week':
        buckets = defaultdict(int)
        for d in dates:
            wk = d.date() - timedelta(days=d.weekday())
            buckets[wk] += 1
        week_start = start - timedelta(days=start.weekday())
        keys = []
        cur = week_start
        while cur <= end:
            keys.append(cur)
            cur += timedelta(days=7)
        labels = [k.strftime('%d/%m') for k in keys]
        values = [buckets.get(k, 0) for k in keys]
        window = 3
    else:  # month
        buckets = defaultdict(int)
        for d in dates:
            buckets[(d.year, d.month)] += 1
        keys = []
        y, m = start.year, start.month
        while (y, m) <= (end.year, end.month):
            keys.append((y, m))
            m += 1
            if m > 12:
                m = 1
                y += 1
        MONTH_ABBR = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
        labels = [MONTH_ABBR[mm - 1] for (yy, mm) in keys]
        values = [buckets.get(k, 0) for k in keys]
        window = 3

    ma = []
    for i in range(len(values)):
        lo = max(0, i - (window - 1))
        w = values[lo:i + 1]
        ma.append(round(sum(w) / len(w), 1))

    top_idx = sorted(range(len(values)), key=lambda i: -values[i])[:3] if values else []

    return {
        'granularity': gran,
        'labels': labels,
        'values': values,
        'ma': ma,
        'top_idx': top_idx,
        'n_days': n_days,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('input', help='Sti til Overskrift.dk JSON-eksport')
    ap.add_argument('--outdir', default=None, help='Output-mappe (default: samme som input)')
    ap.add_argument('--org-name', default=None,
                     help='Visningsnavn til rapport-titel. Default: første citerede term i søgestrengen.')
    ap.add_argument('--known-media', default=None,
                     help='Sti til JSON-liste af kendte medienavne til "mest markante"-udvælgelse. '
                          'Default: indbygget liste af store danske medier.')
    args = ap.parse_args()

    with open(args.input, encoding='utf-8') as f:
        data = json.load(f)

    meta = data['_meta']
    posts = data['posts']

    # --- dedup ---
    seen = set()
    dedup = []
    for p in posts:
        u = p.get('item_url')
        if u in seen:
            continue
        seen.add(u)
        dedup.append(p)
    posts = dedup

    if not posts:
        print('Ingen posts i datasættet efter dedup — stopper.', file=sys.stderr)
        sys.exit(1)

    # --- org-name ---
    org_name = args.org_name
    if not org_name:
        m = re.search(r'"([^"]+)"', meta.get('query', {}).get('searchterm', ''))
        org_name = m.group(1) if m else 'Ukendt søgeterm'

    # --- known media ---
    if args.known_media:
        with open(args.known_media, encoding='utf-8') as f:
            known_media = json.load(f)
    else:
        known_media = DEFAULT_KNOWN_MEDIA

    # --- period ---
    period_from = datetime.fromtimestamp(meta['period']['from'])
    period_to = datetime.fromtimestamp(meta['period']['to'])

    # --- timeline (buckets span the actual post dates; granularity follows their spread) ---
    timeline = build_timeline(posts)
    span_days = timeline.pop('n_days')

    # "Antal dage i perioden" skal matche Overskrift.dk's egen periode-label
    # (fx "30 dage"), som kan afvige med +/-1 fra det faktiske antal kalenderdage
    # mellem første og sidste omtale (afrunding af det relative tidsvindue).
    # Falder tilbage til den beregnede kalenderspredning hvis label ikke matcher.
    label = meta.get('period', {}).get('label', '') or ''
    m = re.match(r'\s*(\d+)\s*dage', label)
    n_days = int(m.group(1)) if m else span_days

    total = len(posts)
    avg_per_day = round(total / n_days, 2) if n_days else 0
    unique_sources = len(set(p.get('title', '?') for p in posts))
    unique_channels = len(set(p.get('groupkey', '?') for p in posts))

    # --- channel distribution ---
    gk_counter = Counter(p.get('groupkey', '?') for p in posts)
    channel_labels, channel_values = [], []
    for gk, cnt in gk_counter.most_common():
        channel_labels.append(GK_TRANSLATE.get(gk, gk.capitalize()))
        channel_values.append(cnt)

    # --- top 10 sources ---
    src_counter = Counter(p.get('title', '?') for p in posts)
    src_url = {}
    for p in posts:
        t = p.get('title', '?')
        if t not in src_url and p.get('siteurl'):
            src_url[t] = p.get('siteurl')
    top_sources = [
        {'label': lbl, 'value': val, 'url': src_url.get(lbl, '')}
        for lbl, val in src_counter.most_common(10)
    ]

    # --- language share ---
    lang_counter = Counter(p.get('language') for p in posts if p.get('language') and p.get('language') != 'None')
    language_share = round(sum(lang_counter.values()) / total, 3) if total else 0
    language_dist = [{'label': k, 'value': v} for k, v in lang_counter.most_common()] if language_share > 0.3 else []

    # --- substantive posts (for the LLM's qualitative theme pass) ---
    substantive_posts = [p for p in posts if is_substantive(p)]
    substantive_out = []
    for i, p in enumerate(substantive_posts):
        substantive_out.append({
            'idx': i,
            'title': clean_text(p.get('item_title')),
            'desc': clean_text(p.get('item_desc'))[:500],
            'src': p.get('title'),
            'groupkey': p.get('groupkey'),
            'date_da': fmt_date_da(p.get('pubdate', '')[:10]),
            'url': p.get('item_url'),
        })

    # --- selected mentions ---
    def mention(p):
        return {
            'title': clean_text(p.get('item_title')),
            'src': p.get('title'),
            'date_da': fmt_date_da(p.get('pubdate', '')[:10]),
            'desc': clean_text(p.get('item_desc'))[:220],
            'url': p.get('item_url'),
        }

    by_date_desc = sorted(posts, key=lambda p: int(p['item_date']), reverse=True)
    newest5 = [mention(p) for p in by_date_desc[:5]]

    notable = [p for p in posts if is_notable(p, known_media)]
    notable_dedup = {}
    for p in notable:
        key = clean_text(p.get('item_title'))
        if key not in notable_dedup:
            notable_dedup[key] = p
    notable5 = [mention(p) for p in
                sorted(notable_dedup.values(), key=lambda p: int(p['item_date']), reverse=True)[:5]]

    metrics = {
        'org_name': org_name,
        'searchterm_display': meta.get('query', {}).get('searchterm', ''),
        'period_label_da': fmt_period_da(period_from, period_to),
        'n_days': n_days,
        'total': total,
        'avg_per_day': avg_per_day,
        'unique_sources': unique_sources,
        'unique_channels': unique_channels,
        'timeline': timeline,
        'channels': {'labels': channel_labels, 'values': channel_values},
        'top_sources': top_sources,
        'language_share': language_share,
        'language_distribution': language_dist,
        'newest5': newest5,
        'notable5': notable5,
        'generated_date_da': datetime.now().strftime('%d/%m-%Y'),
        'substantive_count': len(substantive_out),
    }

    outdir = args.outdir or '.'
    with open(f'{outdir}/metrics.json', 'w', encoding='utf-8') as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    with open(f'{outdir}/substantive.json', 'w', encoding='utf-8') as f:
        json.dump(substantive_out, f, ensure_ascii=False, indent=2)

    print(f"metrics.json og substantive.json skrevet til {outdir}/")
    print(f"  total={total}  dage={n_days}  gns/dag={avg_per_day}  "
          f"kilder={unique_sources}  kanaler={unique_channels}  "
          f"granularitet={timeline['granularity']}  substantielle={len(substantive_out)}")


if __name__ == '__main__':
    main()
