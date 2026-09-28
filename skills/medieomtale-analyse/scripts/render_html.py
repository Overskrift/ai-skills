#!/usr/bin/env python3
"""
render_html.py — Renderer den selvstændige HTML-medieanalyse fra
metrics.json (compute_metrics.py) og topics.json (Claudes kvalitative
mærkesags-analyse, se SKILL.md trin 2).

Al layout, CSS og chart-generering er fast kode her — intet af det skal
genopfindes eller genskrives af Claude fra analyse til analyse. Kun
topics.json's INDHOLD varierer (det kræver læsning/dømmekraft), ikke
strukturen omkring det.

Brug:
    python3 render_html.py <metrics.json> <substantive.json> <topics.json> \
        --logo <overskrift-logo.svg> --out <output.html>
"""
import argparse
import html
import json
import os
import sys
from string import Template

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svg_helpers import hbar_svg, vbar_svg, donut_svg, waffle_svg, apportion_squares, PALETTE  # noqa: E402

REST_GREY = '#d7d9dd'


def esc(s):
    return html.escape(s or '', quote=False)


PAGE_TEMPLATE = Template(r"""<!DOCTYPE html>
<html lang="da">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Medieanalyse: $org_name</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #FEFEFE;
  --header-color: #000000;
  --text: #404040;
  --accent: #FF7500;
  --accent-soft: #FFF4EB;
  --blue: #0055FF;
  --grey: #E9E9E9;
  --bluehint: #F1F6FF;
  --muted: #5d6780;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 8px 18px rgba(0,0,0,0.04);
  --shadow-lg: 0 12px 28px rgba(0,0,0,0.08);
  --radius-sm: 4px; --radius-md: 8px; --radius-lg: 12px;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bluehint);
  color: var(--text);
  font-family: 'Source Sans 3', sans-serif;
  line-height: 1.55;
}
header {
  background: var(--header-color);
  color: #fff;
  padding: 44px 6vw 32px;
  border-bottom: 5px solid var(--accent);
}
header h1 {
  font-family: 'Playfair Display', serif;
  font-size: 2.3rem;
  margin: 0 0 6px;
}
header .sub { color: #cfcfcf; font-size: 1.05rem; }
header .term {
  margin-top: 14px;
  display: inline-block;
  background: rgba(255,117,0,0.15);
  border: 1px solid var(--accent);
  color: #ffd9b3;
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
}
main { max-width: 1100px; margin: 0 auto; padding: 32px 6vw 60px; }
.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
  margin-bottom: 34px;
}
.kpi {
  background: #fff;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: 20px 16px;
  text-align: center;
}
.kpi-val { font-family: 'Playfair Display', serif; font-size: 2rem; font-weight: 800; color: var(--accent); }
.kpi-lbl { font-size: 0.85rem; color: var(--muted); margin-top: 4px; }
section {
  background: #fff;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: 28px 30px;
  margin-bottom: 28px;
}
section h2 { font-family: 'Playfair Display', serif; font-size: 1.4rem; margin: 0 0 6px; color: #1a1a1a; }
section .section-sub { color: var(--muted); font-size: 0.92rem; margin-bottom: 20px; }
.flex-row { display: flex; gap: 28px; align-items: center; flex-wrap: wrap; }
table { width: 100%; border-collapse: collapse; margin-top: 14px; font-size: 0.92rem; }
table th { text-align: left; padding: 8px 10px; border-bottom: 2px solid var(--grey); color: var(--muted); font-weight: 600; }
table td { padding: 8px 10px; border-bottom: 1px solid var(--grey); }
table td.num { text-align: right; font-weight: 600; }
table a { color: var(--blue); text-decoration: none; }
table a:hover { text-decoration: underline; }
.waffle-row { display:flex; gap:34px; align-items:flex-start; flex-wrap:wrap; }
.waffle-cap { font-size:0.78rem; color:var(--muted); margin-top:10px; max-width:280px; }
.topic-legend { flex:1; min-width:300px; font-size:0.92rem; }
.topic-row { display:flex; align-items:flex-start; gap:10px; padding:12px 0; border-bottom:1px solid var(--grey); }
.topic-row:last-child { border-bottom:none; }
.topic-row .swatch { width:12px; height:12px; border-radius:3px; flex-shrink:0; margin-top:4px; }
.topic-row-body { flex:1; min-width:0; }
.topic-row-head { display:flex; align-items:baseline; gap:10px; }
.topic-row-head h3 { font-size:1.02rem; margin:0; color:#1a1a1a; flex:1; }
.topic-row-pct { font-weight:700; color:#1a1a1a; white-space:nowrap; text-align:right; font-size:0.95rem; }
.topic-row-pct small { display:block; font-weight:400; color:var(--muted); font-size:0.75rem; }
.topic-row p { font-size: 0.88rem; color: var(--text); margin: 4px 0 8px; }
.topic-row.rest { opacity:0.75; }
.ex-list { display: flex; flex-direction: column; gap: 6px; }
.ex-item { background: var(--bluehint); border-radius: var(--radius-sm); padding: 7px 10px; font-size: 0.83rem; }
.ex-item a { color: var(--blue); text-decoration: none; font-weight: 600; }
.ex-item a:hover { text-decoration: underline; }
.ex-src { display: block; color: var(--muted); font-size: 0.76rem; margin-top: 2px; }
.mentions-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; }
.mentions-col h4 { font-size: 0.8rem; color: var(--accent); margin: 0 0 12px; text-transform: uppercase; letter-spacing: 0.03em; }
.mention { padding: 12px 0; border-bottom: 1px solid var(--grey); }
.mention:last-child { border-bottom: none; }
.mention-head a { color: #1a1a1a; font-weight: 700; text-decoration: none; font-size: 0.95rem; }
.mention-head a:hover { color: var(--blue); }
.mention-meta { color: var(--muted); font-size: 0.78rem; margin: 3px 0 6px; }
.mention-desc { font-size: 0.85rem; color: var(--text); }
.footer { display: flex; justify-content: space-between; align-items: center; padding: 24px 6vw 40px; color: var(--muted); font-size: 0.85rem; flex-wrap: wrap; gap: 12px; }
.footer a { color: var(--blue); }
@media (max-width: 700px) {
  .mentions-grid { grid-template-columns: 1fr; }
  header h1 { font-size: 1.7rem; }
}
</style>
</head>
<body>
<header>
  <h1>Medieanalyse: $org_name</h1>
  <div class="sub">Periode: $period_label_da &middot; Kilde: Overskrift.dk</div>
  <div class="term">S&oslash;geterm: $searchterm_display_esc</div>
</header>

<main>
  <div class="kpi-row">
    $kpi_html
  </div>

  <section>
    <h2>Omtaler over tid</h2>
    <div class="section-sub">$timeline_sub</div>
    $timeline_svg
  </section>

  <section>
    <h2>Kanalfordeling</h2>
    <div class="section-sub">Fordeling af de $total omtaler p&aring; kanaltype.</div>
    <div class="flex-row">
      <div style="flex-shrink:0">$donut_svg</div>
      <div>$donut_legend</div>
    </div>
  </section>

  <section>
    <h2>Top 10 kilder</h2>
    <div class="section-sub">De mest aktive afsendere.</div>
    $hbar_svg
    <table>
      <thead><tr><th>Kilde</th><th class="num">Omtaler</th></tr></thead>
      <tbody>
        $top_src_rows
      </tbody>
    </table>
  </section>

  <section>
    <h2>Top 5 m&aelig;rkesager</h2>
    <div class="section-sub">De temaer og diskussioner der fylder mest i omtalerne i perioden &mdash; hvert felt i gitteret er 1% af samtlige $total omtaler, ikke kun af summen af top 5.</div>
    <div class="waffle-row">
      <div style="flex-shrink:0">
        $waffle_svg
        <div class="waffle-cap">L&aelig;ses r&aelig;kke for r&aelig;kke, &oslash;verst til venstre. Hvert felt = 1% af alle omtaler i perioden.</div>
      </div>
      <div class="topic-legend">
        $topic_rows
      </div>
    </div>
  </section>

  $language_section

  <section>
    <h2>Udvalgte omtaler</h2>
    <div class="mentions-grid">
      <div class="mentions-col">
        <h4>5 seneste omtaler</h4>
        $newest_html
      </div>
      <div class="mentions-col">
        <h4>5 mest markante medier</h4>
        $notable_html
      </div>
    </div>
  </section>
</main>

<div class="footer">
  <span>Analyse genereret $generated_date_da &middot; Datakilde: <a href="https://overskrift.dk" target="_blank" rel="noopener">Overskrift.dk</a></span>
  <div style="width:120px;opacity:0.7">$logo_svg</div>
</div>

</body>
</html>
""")

TIMELINE_SUB_BY_GRANULARITY = {
    'hour': 'S&oslash;jler viser antal omtaler pr. time. Orange tal markerer de tre timer med flest omtaler.',
    'day': 'S&oslash;jler viser antal omtaler pr. dag. Den bl&aring; linje er et glidende gennemsnit. Orange tal markerer de tre dage med flest omtaler.',
    'week': 'S&oslash;jler viser antal omtaler pr. uge (mandag som ugestart). Den bl&aring; linje er et glidende gennemsnit. Orange tal markerer de tre uger med flest omtaler.',
    'month': 'S&oslash;jler viser antal omtaler pr. m&aring;ned. Orange tal markerer de tre m&aring;neder med flest omtaler.',
}


def mention_card(m):
    desc = m['desc']
    ellipsis = '&hellip;' if len(desc) >= 220 else ''
    return (
        '<div class="mention">'
        f'<div class="mention-head"><a href="{esc(m["url"])}" target="_blank" rel="noopener">{esc(m["title"])}</a></div>'
        f'<div class="mention-meta">{esc(m["src"])} &middot; {esc(m["date_da"])}</div>'
        f'<div class="mention-desc">{esc(desc)}{ellipsis}</div>'
        '</div>'
    )


def topic_row(t, color, pct, is_rest=False):
    """Én række i mærkesags-legenden ved siden af waffle-diagrammet.

    pct er andelen af det SAMLEDE antal omtaler (metrics['total']), ikke af
    summen af top 5 — det er hele pointen med at vise et waffle-gitter frem
    for fx et kagediagram, hvor kun top-5-summen typisk ville udgøre 100%.
    """
    ex_html = ''
    for e in t.get('examples', []):
        ex_html += (
            '<div class="ex-item">'
            f'<a href="{esc(e["url"])}" target="_blank" rel="noopener">{esc(e["title"])}</a>'
            f'<span class="ex-src">{esc(e["src"])}</span>'
            '</div>\n'
        )
    pct_str = f'{pct:.1f}'.replace('.', ',')
    cls = 'topic-row rest' if is_rest else 'topic-row'
    return f"""
    <div class="{cls}">
      <span class="swatch" style="background:{color}"></span>
      <div class="topic-row-body">
        <div class="topic-row-head">
          <h3>{esc(t['title'])}</h3>
          <div class="topic-row-pct">{pct_str}%<small>{t['count']} omtaler</small></div>
        </div>
        <p>{esc(t['desc'])}</p>
        <div class="ex-list">{ex_html}</div>
      </div>
    </div>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('metrics', help='Sti til metrics.json')
    ap.add_argument('substantive', help='Sti til substantive.json (bruges til at slå example_idx op)')
    ap.add_argument('topics', help='Sti til topics.json (Claudes kvalitative temaanalyse)')
    ap.add_argument('--logo', required=True, help='Sti til overskrift-logo.svg')
    ap.add_argument('--out', required=True, help='Output HTML-fil')
    args = ap.parse_args()

    metrics = json.load(open(args.metrics, encoding='utf-8'))
    substantive = json.load(open(args.substantive, encoding='utf-8'))
    topics_data = json.load(open(args.topics, encoding='utf-8'))
    logo_svg = open(args.logo, encoding='utf-8').read()

    sub_by_idx = {p['idx']: p for p in substantive}

    # ---- KPIs ----
    kpis = [
        ('Samlede omtaler', str(metrics['total'])),
        ('Gns. pr. dag', str(metrics['avg_per_day'])),
        ('Unikke kilder', str(metrics['unique_sources'])),
        ('Kanaler i spil', str(metrics['unique_channels'])),
        ('Analyseperiode', f"{metrics['n_days']} dage"),
    ]
    kpi_html = ''.join(
        f'<div class="kpi"><div class="kpi-val">{esc(v)}</div><div class="kpi-lbl">{esc(k)}</div></div>'
        for k, v in kpis
    )

    # ---- timeline ----
    tl = metrics['timeline']
    timeline_svg = vbar_svg(tl['labels'], tl['values'], ma=tl['ma'], top_idx=tl['top_idx'], w=900, h=260)
    timeline_sub = TIMELINE_SUB_BY_GRANULARITY.get(tl['granularity'], TIMELINE_SUB_BY_GRANULARITY['day'])

    # ---- channels ----
    donut, legend = donut_svg(metrics['channels']['labels'], metrics['channels']['values'], size=240)

    # ---- top sources ----
    hbar = hbar_svg([s['label'] for s in metrics['top_sources']], [s['value'] for s in metrics['top_sources']])
    top_src_rows = ''
    for s in metrics['top_sources']:
        link = f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["label"])}</a>' if s['url'] else esc(s['label'])
        top_src_rows += f"<tr><td>{link}</td><td class='num'>{s['value']}</td></tr>\n"

    # ---- topics: waffle-diagram (andel af SAMLEDE omtaler) + legende ----
    # topics.json skal indeholde præcis 5 temaer (SKILL.md trin 2). "Øvrige"
    # er alt i metrics['total'] der ikke er dækket af de 5 temaer, og tælles
    # altid med som en 6. — grå — kategori i gitteret, så de 100 felter altid
    # summer til det fulde datasæt, ikke kun til top 5.
    topics_list = topics_data['topics']
    counts = [t['count'] for t in topics_list]
    rest_count = max(0, metrics['total'] - sum(counts))
    all_counts = counts + [rest_count]
    squares = apportion_squares(all_counts, n_squares=100)  # summer altid til nøjagtig 100 -> fast 10x10-gitter

    colors = [PALETTE[i % len(PALETTE)] for i in range(len(topics_list))] + [REST_GREY]
    square_colors = []
    for color, n_sq in zip(colors, squares):
        square_colors.extend([color] * n_sq)
    waffle = waffle_svg(square_colors, cols=10, rows=10)

    topic_rows_html = ''
    for i, t in enumerate(topics_list):
        color = PALETTE[i % len(PALETTE)]
        examples = []
        for idx in t['example_idx']:
            p = sub_by_idx.get(idx)
            if p:
                examples.append({'title': p['title'], 'src': p['src'], 'url': p['url']})
        pct = 100 * t['count'] / metrics['total'] if metrics['total'] else 0
        topic_rows_html += topic_row({**t, 'examples': examples}, color, pct)
    if rest_count > 0:
        rest_pct = 100 * rest_count / metrics['total'] if metrics['total'] else 0
        topic_rows_html += topic_row(
            {'title': 'Øvrige omtaler', 'desc': 'Alt andet i datasættet: enkeltstående nyheder, opslag uden for top 5, sociale medier m.m.',
             'count': rest_count, 'example_idx': []},
            REST_GREY, rest_pct, is_rest=True,
        )

    # ---- language section (optional) ----
    if metrics.get('language_distribution'):
        lang_donut, lang_legend = donut_svg(
            [d['label'] for d in metrics['language_distribution']],
            [d['value'] for d in metrics['language_distribution']],
            size=200,
        )
        language_section = f"""<section>
    <h2>Sprogfordeling</h2>
    <div class="section-sub">Sprog registreret p&aring; mindst 30% af omtalerne.</div>
    <div class="flex-row"><div style="flex-shrink:0">{lang_donut}</div><div>{lang_legend}</div></div>
  </section>"""
    else:
        language_section = ''

    # ---- mentions ----
    newest_html = '\n'.join(mention_card(m) for m in metrics['newest5'])
    notable_html = '\n'.join(mention_card(m) for m in metrics['notable5'])

    html_doc = PAGE_TEMPLATE.substitute(
        org_name=esc(metrics['org_name']),
        period_label_da=esc(metrics['period_label_da']),
        searchterm_display_esc=esc(metrics['searchterm_display']),
        kpi_html=kpi_html,
        timeline_sub=timeline_sub,
        timeline_svg=timeline_svg,
        total=metrics['total'],
        donut_svg=donut,
        donut_legend=legend,
        hbar_svg=hbar,
        top_src_rows=top_src_rows,
        waffle_svg=waffle,
        topic_rows=topic_rows_html,
        language_section=language_section,
        newest_html=newest_html,
        notable_html=notable_html,
        generated_date_da=esc(metrics['generated_date_da']),
        logo_svg=logo_svg,
    )

    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(html_doc)
    print(f"Skrev {len(html_doc)} tegn til {args.out}")


if __name__ == '__main__':
    main()
