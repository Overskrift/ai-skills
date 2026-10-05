#!/usr/bin/env python3
"""
compute_metrics.py: Deterministisk beregning af alle metrikker til en
medieomtale-analyse (Overskrift.dk JSON).

Gør ALT det mekaniske arbejde, som ellers ville blive genopfundet i hver
analyse: dedup, KPI'er, tidslinje (med automatisk granularitet), kanal-
fordeling, top-10 kilder, dansk datoformatering, "substantielle" posts til
den kvalitative mærkesags-analyse, samt nyeste/mest markante omtaler.

Det ENESTE trin skillen stadig kræver agentens dømmekraft til, er "Top 5
mærkesager" (semantisk tema-identifikation). Det gøres IKKE her, men i et
efterfølgende trin hvor agenten læser substantive.json og skriver topics.json.

Brug:
    python3 compute_metrics.py <input.json> [--outdir <dir>] [--org-name "Navn"]
                               [--known-media <liste.json>] [--tz Europe/Copenhagen]

Output (i --outdir, default: samme mappe som input; oprettes hvis den mangler):
    metrics.json      alle kvantitative metrikker, klar til rendering
    substantive.json  filtrerede posts til den kvalitative temaanalyse

Alle tidspunkter fortolkes i periodens tidszone (_meta.period.timezone, ellers
--tz, default Europe/Copenhagen), uanset maskinens egen tidszone. Det betyder
noget i sandkasser der kører i UTC.
"""
import argparse
import html
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9
    ZoneInfo = None

MONTHS_DA = ['januar', 'februar', 'marts', 'april', 'maj', 'juni', 'juli',
             'august', 'september', 'oktober', 'november', 'december']

GK_TRANSLATE = {
    'websites': 'Nyhedssites', 'facebook': 'Facebook', 'linkedin': 'LinkedIn',
    'twitter': 'Twitter/X', 'instagram': 'Instagram', 'youtube': 'YouTube',
    'podcast': 'Podcast', 'blogs': 'Blogs', 'reddit': 'Reddit', 'bluesky': 'Bluesky',
    'trustpilot': 'Trustpilot', 'mastodon': 'Mastodon',
}

# Matches på hele ord (tokens), ikke delstrenge: "DR" rammer "DR Nyheder" og
# "dr.dk", men ikke "Andreas" eller "Fredrik". "B.T." normaliseres til "bt".
DEFAULT_KNOWN_MEDIA = [
    'DR', 'DR Nyheder', 'Politiken', 'BT', 'TV 2', 'TV2', 'Berlingske',
    'Jyllands-Posten', 'JP', 'Ekstra Bladet', 'Finans', 'Børsen', 'Altinget', 'Information',
    'SE og HØR', 'JydskeVestkysten', 'Kristeligt Dagblad', 'Weekendavisen', 'Ritzau',
    'Zetland', 'Avisen.dk',
]

# Query-parametre der kun er tracking og ikke ændrer hvilken artikel URL'en peger på.
TRACKING_PARAM = re.compile(
    r'^(utm_.*|referrer|ref|ref_src|fbclid|gclid|dclid|mc_cid|mc_eid|igshid|xtor|cmpid|'
    r'at_medium|at_campaign|at_creation|at_format|at_link|_ga|_gl|ocid|smid|share)$', re.I)


# ---------------------------------------------------------------- helpers ---

def get_tz(name):
    if ZoneInfo is None:
        print('ADVARSEL: zoneinfo findes ikke (Python < 3.9); bruger maskinens tidszone.', file=sys.stderr)
        return None
    try:
        return ZoneInfo(name)
    except Exception:
        print(f'ADVARSEL: ukendt tidszone "{name}" (mangler tzdata?); bruger maskinens tidszone.',
              file=sys.stderr)
        return None


def clean_text(s):
    """Fjern HTML-tags og afkod alle HTML-entiteter.

    <mark>-tags fra Overskrifts søge-highlight kan sidde midt i et ord
    ("Musik i Leje<mark>t"), så de fjernes UDEN mellemrum. Alle andre tags
    erstattes med mellemrum, så ord på hver side af fx <br> ikke klistres sammen.
    """
    if not s:
        return ''
    s = re.sub(r'</?mark\b[^>]*>', '', s, flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = html.unescape(s)
    return re.sub(r'\s+', ' ', s).strip()


def norm_url(u):
    """URL-nøgle til dedup: uden tracking-parametre og fragment."""
    if not u:
        return None
    try:
        parts = urlsplit(u.strip())
    except ValueError:
        return u.strip()
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not TRACKING_PARAM.match(k)]
    path = parts.path.rstrip('/') or '/'
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ''))


def name_tokens(s):
    """'B.T.' -> ['bt'], 'Kultur | Berlingske' -> ['kultur', 'berlingske'], 'dr.dk' -> ['dr', 'dk']."""
    toks = re.findall(r'[0-9a-zæøåäöüé]+', (s or '').lower())
    out, run = [], ''
    for t in toks:  # saml forkortelser som b.t. -> bt
        if len(t) == 1 and t.isalpha():
            run += t
            continue
        if run:
            out.append(run)
            run = ''
        out.append(t)
    if run:
        out.append(run)
    return out


def contains_tokens(hay, needle):
    n = len(needle)
    return n > 0 and any(hay[i:i + n] == needle for i in range(len(hay) - n + 1))


def fmt_date_da(dt):
    return dt.strftime('%d/%m-%Y') if dt else ''


def fmt_period_da(d_from, d_to):
    def one(d):
        return f"{d.day}. {MONTHS_DA[d.month - 1]} {d.year}"
    return f"{one(d_from)} – {one(d_to)}"


def pick_granularity(n_days):
    if n_days <= 3:
        return 'hour'
    if n_days <= 60:
        return 'day'
    if n_days <= 186:  # ca. 6 måneder
        return 'week'
    return 'month'


def search_phrases(searchterm, org_name):
    """Fraser der bruges til at vurdere om en titel handler om emnet."""
    st = re.sub(r'-\([^)]*\)', ' ', searchterm or '')       # fjern stopord-grupper
    st = re.sub(r'-"[^"]*"|-\S+', ' ', st)                    # fjern -"..." og -ord
    phrases = [p.lower() for p in re.findall(r'"([^"]+)"', st)]
    if not phrases:
        rest = re.sub(r'"[^"]*"', ' ', st)
        phrases = [w.strip('+*()~0123456789').lower() for w in rest.split()]
    if org_name:
        phrases.append(org_name.lower())
    return [p for p in phrases if len(p) >= 4]


def is_substantive(p):
    """Har opslaget tekst nok til at indgå i tema-analysen?

    Afgøres af brødtekstens længde, ikke af titlen: "Fotos fra <side>" kan
    sagtens have et langt, relevant opslag med.
    """
    title = clean_text(p.get('item_title'))
    desc = clean_text(p.get('item_desc'))
    ch = p.get('groupkey', '')
    if ch in ('instagram', 'facebook') and len(desc) < 40:
        return False
    if re.match(r'^(foto|fotos|video)\s+(fra|af)\b', title.lower()) and len(desc) < 40:
        return False
    if len(desc) < 5 and len(title) < 5:
        return False
    return True


# --------------------------------------------------------------- timeline ---

def build_timeline(post_dts, d_from, d_to):
    """Buckets dækker HELE perioden (også tomme dage/timer i kanterne)."""
    start = min([d_from] + [d.date() for d in post_dts])
    end = max([d_to] + [d.date() for d in post_dts])
    n_days = (end - start).days + 1
    gran = pick_granularity(n_days)
    buckets = defaultdict(int)

    if gran == 'hour':
        for d in post_dts:
            buckets[d.replace(minute=0, second=0, microsecond=0, tzinfo=None)] += 1
        keys = []
        cur = datetime(start.year, start.month, start.day)
        stop = datetime(end.year, end.month, end.day, 23)
        while cur <= stop:
            keys.append(cur)
            cur += timedelta(hours=1)
        labels = [k.strftime('%d/%m %Hh') for k in keys]
        window = 3
    elif gran == 'day':
        for d in post_dts:
            buckets[d.date()] += 1
        keys = [start + timedelta(days=i) for i in range(n_days)]
        labels = [k.strftime('%d/%m') for k in keys]
        window = 7
    elif gran == 'week':
        for d in post_dts:
            buckets[d.date() - timedelta(days=d.weekday())] += 1
        cur = start - timedelta(days=start.weekday())
        keys = []
        while cur <= end:
            keys.append(cur)
            cur += timedelta(days=7)
        labels = [k.strftime('%d/%m') for k in keys]
        window = 3
    else:
        for d in post_dts:
            buckets[(d.year, d.month)] += 1
        keys = []
        y, m = start.year, start.month
        while (y, m) <= (end.year, end.month):
            keys.append((y, m))
            m += 1
            if m > 12:
                m, y = 1, y + 1
        abbr = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
        span_years = keys[-1][0] != keys[0][0]
        labels = [f"{abbr[mm - 1]} {str(yy)[2:]}" if span_years else abbr[mm - 1] for (yy, mm) in keys]
        window = 3

    values = [buckets.get(k, 0) for k in keys]
    ma = []
    for i in range(len(values)):
        w = values[max(0, i - (window - 1)):i + 1]
        ma.append(round(sum(w) / len(w), 1))
    top_idx = [i for i in sorted(range(len(values)), key=lambda i: -values[i])[:3] if values[i] > 0]

    return {'granularity': gran, 'labels': labels, 'values': values, 'ma': ma, 'top_idx': top_idx}


# ------------------------------------------------------------------- main ---

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('input', help='Sti til Overskrift.dk JSON-eksport')
    ap.add_argument('--outdir', default=None, help='Output-mappe (default: samme mappe som input)')
    ap.add_argument('--org-name', default=None,
                    help='Visningsnavn til rapport-titel. Default: første citerede term i søgestrengen.')
    ap.add_argument('--known-media', default=None,
                    help='Sti til JSON-liste af kendte medienavne til "mest markante"-udvælgelse. '
                         'Default: indbygget liste af store danske medier.')
    ap.add_argument('--tz', default='Europe/Copenhagen',
                    help='Tidszone hvis _meta.period.timezone mangler (default Europe/Copenhagen)')
    args = ap.parse_args()

    with open(args.input, encoding='utf-8') as f:
        data = json.load(f)
    meta = data.get('_meta', {})
    raw_posts = data.get('posts', [])

    tz = get_tz(meta.get('period', {}).get('timezone') or args.tz)

    def local(ts):
        return datetime.fromtimestamp(int(ts), tz)

    # --- dedup på normaliseret URL; behold versionen med længst tekst ---
    by_key, order = {}, []
    for i, p in enumerate(raw_posts):
        key = norm_url(p.get('item_url')) or f'__nourl_{i}'
        if key not in by_key:
            by_key[key] = p
            order.append(key)
        elif len(p.get('item_desc') or '') > len(by_key[key].get('item_desc') or ''):
            by_key[key] = p
    posts = [by_key[k] for k in order]
    n_dupes = len(raw_posts) - len(posts)

    if not posts:
        print('Ingen posts i datasættet efter dedup. Stopper.', file=sys.stderr)
        sys.exit(1)

    # --- LinkedIn: kildenavne varierer pr. afsender; saml dem som én kilde ---
    for p in posts:
        if p.get('groupkey') == 'linkedin':
            p['title'] = 'LinkedIn'
            p['siteurl'] = 'https://www.linkedin.com'

    for p in posts:
        p['_dt'] = local(p['item_date'])

    # --- org-name ---
    searchterm = meta.get('query', {}).get('searchterm', '')
    org_name = args.org_name
    if not org_name:
        m = re.search(r'"([^"]+)"', searchterm)
        org_name = m.group(1) if m else 'Ukendt søgeterm'

    known_media = DEFAULT_KNOWN_MEDIA
    if args.known_media:
        with open(args.known_media, encoding='utf-8') as f:
            known_media = json.load(f)
    known_tokens = [name_tokens(k) for k in known_media]

    # --- periode: altid fra _meta.period.from/to, ikke fra den menneskelige label ---
    period = meta.get('period', {})
    if period.get('from') and period.get('to'):
        d_from, d_to = local(period['from']).date(), local(period['to']).date()
    else:
        print('ADVARSEL: _meta.period mangler; bruger første/sidste omtales dato.', file=sys.stderr)
        d_from = min(p['_dt'] for p in posts).date()
        d_to = max(p['_dt'] for p in posts).date()
    n_days = (d_to - d_from).days + 1

    timeline = build_timeline([p['_dt'] for p in posts], d_from, d_to)

    total = len(posts)
    avg_per_day = round(total / n_days, 2) if n_days else 0
    unique_sources = len(set(p.get('title', '?') for p in posts))
    unique_channels = len(set(p.get('groupkey', '?') for p in posts))

    gk_counter = Counter(p.get('groupkey', '?') for p in posts)
    unknown_gk = [gk for gk in gk_counter if gk not in GK_TRANSLATE]
    if unknown_gk:
        print(f'BEMÆRK: kanaltyper uden dansk navn (tilføj til GK_TRANSLATE): {unknown_gk}', file=sys.stderr)
    channel_labels = [GK_TRANSLATE.get(gk, gk.capitalize()) for gk, _ in gk_counter.most_common()]
    channel_values = [cnt for _, cnt in gk_counter.most_common()]

    src_counter = Counter(p.get('title', '?') for p in posts)
    src_url = {}
    for p in posts:
        t = p.get('title', '?')
        if t not in src_url and p.get('siteurl'):
            src_url[t] = p['siteurl']
    top_sources = [{'label': lbl, 'value': val, 'url': src_url.get(lbl, '')}
                   for lbl, val in src_counter.most_common(10)]

    lang_counter = Counter(p.get('language') for p in posts
                           if p.get('language') and p.get('language') != 'None')
    language_share = round(sum(lang_counter.values()) / total, 3) if total else 0
    language_dist = ([{'label': k, 'value': v} for k, v in lang_counter.most_common()]
                     if language_share > 0.3 else [])

    # --- substantielle posts til tema-analysen ---
    substantive_out = []
    for p in posts:
        if not is_substantive(p):
            continue
        substantive_out.append({
            'idx': len(substantive_out),
            'title': clean_text(p.get('item_title')),
            'desc': clean_text(p.get('item_desc'))[:500],
            'src': p.get('title'),
            'groupkey': p.get('groupkey'),
            'date_da': fmt_date_da(p['_dt']),
            'url': p.get('item_url'),
        })

    def mention(p):
        return {
            'title': clean_text(p.get('item_title')),
            'src': p.get('title'),
            'date_da': fmt_date_da(p['_dt']),
            'desc': clean_text(p.get('item_desc'))[:220],
            'url': p.get('item_url'),
        }

    newest5 = [mention(p) for p in sorted(posts, key=lambda p: int(p['item_date']), reverse=True)[:5]]

    # --- mest markante: kendte medier, hvor emnet står i titlen, først ---
    phrases = search_phrases(searchterm, org_name)

    def about_topic(p):
        t = clean_text(p.get('item_title')).lower()
        return any(ph in t for ph in phrases)

    notable = [p for p in posts
               if any(contains_tokens(name_tokens(p.get('title')), kt) for kt in known_tokens)]
    notable_dedup = {}
    for p in sorted(notable, key=lambda p: (about_topic(p), p.get('groupkey') == 'websites',
                                            int(p['item_date'])), reverse=True):
        notable_dedup.setdefault(clean_text(p.get('item_title')).lower(), p)
    notable5 = [mention(p) for p in list(notable_dedup.values())[:5]]

    metrics = {
        'org_name': org_name,
        'searchterm_display': searchterm,
        'period_label_da': fmt_period_da(d_from, d_to),
        'n_days': n_days,
        'total': total,
        'duplicates_removed': n_dupes,
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
        'generated_date_da': fmt_date_da(datetime.now(tz)),
        'substantive_count': len(substantive_out),
    }

    outdir = args.outdir or os.path.dirname(os.path.abspath(args.input))
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, 'metrics.json'), 'w', encoding='utf-8') as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    with open(os.path.join(outdir, 'substantive.json'), 'w', encoding='utf-8') as f:
        json.dump(substantive_out, f, ensure_ascii=False, indent=2)

    print(f"metrics.json og substantive.json skrevet til {outdir}/")
    print(f"  total={total} (dubletter fjernet: {n_dupes})  dage={n_days}  gns/dag={avg_per_day}  "
          f"kilder={unique_sources}  kanaler={unique_channels}  "
          f"granularitet={timeline['granularity']}  substantielle={len(substantive_out)}")


if __name__ == '__main__':
    main()
