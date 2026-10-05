"""
svg_helpers.py: Genbrugelige SVG-chart-funktioner til medieomtale-analyse.
Importeres af render_html.py og resolve_topics.py (from svg_helpers import ...).
"""
import math
from html import escape as _esc


def _x(s):
    """Escape tekst til SVG/HTML-indhold."""
    return _esc(str(s), quote=False)

PALETTE = ['#FF7500','#0055FF','#16a34a','#7c3aed','#0d9488','#db2777','#ca8a04','#4338ca','#65a30d','#0891b2']


def fmt_num(n):
    """Kortere talformat til y-akse: 1200 → '1,2k', 45 → '45'."""
    if n >= 1000:
        return f'{n/1000:.1f}k'.replace('.0k', 'k')
    return str(int(n))


def fmt_xlabel(lbl, n_total):
    """X-akse label. Labels fra compute_metrics.py er allerede korte
    ('28/09', '28/09 14h', 'Okt'), og vbar_svg viser højst ca. 14 af dem,
    så de vises uforkortede. Timelabels bevarer datoen, så flere døgn ikke
    kan forveksles."""
    return lbl


def _label_step(labels):
    """Hvor mange søjler der springes over mellem x-labels (højst ca. 14 labels).
    For time-data vælges et trin der går op i et døgn (1, 2, 3, 4, 6, 12, 24)."""
    n = len(labels)
    target = max(1, -(-n // 14))
    if labels and str(labels[0]).endswith('h'):
        for s in (1, 2, 3, 4, 6, 12, 24):
            if s >= target:
                return s
    return target


def hbar_svg(labels, values, colors=None):
    """Vandret søjlediagram — til top-10 kilder og nøgleord.

    Labels trunkeres til maks 40 tegn; meget lange wraps over to linjer.
    Returnerer en SVG-streng klar til indlejring i HTML.
    """
    if not values:
        return '<p>Ingen data</p>'
    max_v = max(values) or 1
    bar_h = 30
    total_h = len(values) * (bar_h + 6) + 20
    lw = 185  # label-bredde
    bw = 340  # søjle-areal
    svg = f'<svg viewBox="0 0 {lw+bw+60} {total_h}" overflow="visible" xmlns="http://www.w3.org/2000/svg" style="width:100%;font-family:sans-serif">\n'
    for i, (lbl, val) in enumerate(zip(labels, values)):
        lbl = lbl if len(lbl) <= 40 else lbl[:39] + '…'
        y = i * (bar_h + 6) + 10
        blen = int(bw * val / max_v)
        col = (colors or PALETTE)[i % len(colors or PALETTE)]
        words = lbl.split()
        if len(lbl) > 24 and len(words) == 1:
            lbl, words = lbl[:23] + '…', [lbl[:23] + '…']
        if len(lbl) > 24:
            mid = max(1, len(words) // 2)
            line1 = _x(' '.join(words[:mid]))
            line2 = _x(' '.join(words[mid:]))
            svg += f'  <text x="{lw-8}" y="{y+bar_h//2-3}" text-anchor="end" font-size="11" fill="#475569">{line1}</text>\n'
            svg += f'  <text x="{lw-8}" y="{y+bar_h//2+10}" text-anchor="end" font-size="11" fill="#475569">{line2}</text>\n'
        else:
            lbl_esc = _x(lbl)
            svg += f'  <text x="{lw-8}" y="{y+bar_h//2+5}" text-anchor="end" font-size="12" fill="#475569">{lbl_esc}</text>\n'
        svg += f'  <rect x="{lw}" y="{y}" width="{blen}" height="{bar_h}" fill="{col}" rx="3"/>\n'
        svg += f'  <text x="{lw+blen+6}" y="{y+bar_h//2+5}" font-size="12" fill="#1e293b">{val}</text>\n'
    svg += '</svg>'
    return svg


def _nice_axis_max(v, ticks=4):
    """Rund aksens maksimum op, så alle 5 gitterlinjer får pæne heltal
    (fx 0, 1, 2, 3, 4 i stedet for 0, 0, 0, 0, 1 ved små tal)."""
    raw = v / ticks
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    for m in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        step = m * mag
        if step >= raw and step >= 1 and float(step).is_integer():
            return step * ticks
    return math.ceil(raw) * ticks


def vbar_svg(labels, values, ma=None, top_idx=None, w=700, h=240):
    """Lodret søjlediagram med valgfri glidende gennemsnit-linje — til tidslinje.

    - overflow="visible" sikrer at roterede x-labels ikke klipper mod viewBox-kanten
    - pad_b=70 giver plads til labels roteret -40 grader
    - fmt_xlabel() forkorter labels automatisk baseret på antal datapunkter
    - fmt_num() giver kortere y-akse værdier (fx '1,2k' i stedet for '1200')
    - top_idx: liste af indeks der markeres med talværdi øverst (topdage)
    """
    if not values:
        return '<p>Ingen data</p>'
    ma_clean = [v for v in (ma or []) if v is not None]
    max_v = _nice_axis_max(max(max(values), max(ma_clean) if ma_clean else 0) or 1)
    n = len(values)
    pad_l, pad_r, pad_t, pad_b = 42, 15, 15, 70
    cw = w - pad_l - pad_r
    ch = h - pad_t - pad_b
    bw = max(2, int(cw / n) - 1)
    svg = f'<svg viewBox="0 0 {w} {h}" overflow="visible" xmlns="http://www.w3.org/2000/svg" style="width:100%;font-family:sans-serif">\n'
    # Y-akse gridlinjer og værdier
    for yi in range(0, 5):
        ypos = pad_t + ch - int(ch * yi / 4)
        val_lbl = fmt_num(max_v * yi / 4)
        svg += f'  <line x1="{pad_l}" y1="{ypos}" x2="{w-pad_r}" y2="{ypos}" stroke="#e2e8f0" stroke-width="1"/>\n'
        svg += f'  <text x="{pad_l-5}" y="{ypos+4}" text-anchor="end" font-size="10" fill="#94a3b8">{val_lbl}</text>\n'
    # Søjler
    for i, val in enumerate(values):
        x = pad_l + i * (cw / n)
        bh = int(ch * val / max_v)
        svg += f'  <rect x="{x:.1f}" y="{pad_t+ch-bh}" width="{bw}" height="{bh}" fill="rgba(255,117,0,0.65)" rx="1"/>\n'
    # Glidende gennemsnit-linje
    if ma:
        pts = [f'{pad_l + i*(cw/n) + bw/2:.1f},{pad_t + ch - ch*v/max_v:.1f}'
               for i, v in enumerate(ma) if v is not None]
        if pts:
            svg += f'  <polyline points="{" ".join(pts)}" fill="none" stroke="#0055FF" stroke-width="2.5"/>\n'
    # Topdags-annotationer
    for idx in (top_idx or []):
        x = pad_l + idx * (cw / n) + bw / 2
        bh = int(ch * values[idx] / max_v)
        y_top = pad_t + ch - bh - 6
        svg += f'  <text x="{x:.1f}" y="{y_top:.1f}" text-anchor="middle" font-size="10" font-weight="bold" fill="#FF7500">{values[idx]}</text>\n'
    # X-akse labels
    step = _label_step(labels)
    for i in range(0, n, step):
        x = pad_l + i * (cw / n) + bw / 2
        lbl = _x(fmt_xlabel(labels[i], n)) if i < len(labels) else ''
        svg += f'  <text x="{x:.1f}" y="{pad_t+ch+14}" text-anchor="end" font-size="10" fill="#64748b" transform="rotate(-38,{x:.1f},{pad_t+ch+14})">{lbl}</text>\n'
    svg += '</svg>'
    return svg


def apportion_squares(values, n_squares=100):
    """Fordeler `values` (fx omtale-tal pr. mærkesag + "øvrige") over præcis
    `n_squares` felter, uanset afrundingsfejl — bruges af waffle_svg().

    Simpel per-værdi afrunding (fx round(v/total*100)) kan let summe til 87
    eller 103 felter i stedet for 100, hvilket ødelægger et fast 10×10-gitter.
    Denne funktion bruger "largest remainder"-metoden: alle værdier rundes ned,
    og de resterende felter fordeles ét ad gangen til de værdier der har den
    største rest — det garanterer sum(resultat) == n_squares altid.

    Derudover: enhver værdi > 0 der ville runde ned til 0 felter (dvs. en reel
    mærkesag der ellers ville forsvinde visuelt) får mindst 1 felt, taget fra
    den værdi der har flest felter (typisk "øvrige").
    """
    total = sum(values)
    if total <= 0:
        return [0] * len(values)
    raw = [v / total * n_squares for v in values]
    floors = [int(x) for x in raw]
    remainder = n_squares - sum(floors)
    order = sorted(range(len(values)), key=lambda i: raw[i] - floors[i], reverse=True)
    for i in order[:remainder]:
        floors[i] += 1
    # Sikr at ingen reel værdi (>0) ender på 0 felter, ved at låne fra det største felt
    for i, v in enumerate(values):
        if v > 0 and floors[i] == 0:
            donor = max(range(len(floors)), key=lambda j: floors[j])
            if donor != i and floors[donor] > 1:
                floors[donor] -= 1
                floors[i] += 1
    return floors


def waffle_svg(square_colors, cols=10, rows=10, cell=24, gap=4):
    """Waffle-/piktogram-diagram: et fast cols×rows-gitter (default 10×10 = 100
    felter), hvor hvert felt farves efter `square_colors` (en liste med præcis
    cols*rows farve-hex-strenge — se apportion_squares() for at komme dertil
    fra rå omtale-tal). Læses rækkevis, øverst til venstre.

    Bruges i stedet for et kagediagram når én kategori ("øvrige") dominerer
    kraftigt — vinkler i en donut er svære at sammenligne præcist ved små
    andele, mens felter i et fast gitter kan tælles og sammenlignes 1:1.
    """
    n = cols * rows
    if len(square_colors) != n:
        raise ValueError(f'waffle_svg forventer præcis {n} farver, fik {len(square_colors)}')
    w = cols * cell + (cols - 1) * gap
    h = rows * cell + (rows - 1) * gap
    svg = f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg" style="display:block">\n'
    for i, col in enumerate(square_colors):
        c, r = i % cols, i // cols
        x = c * (cell + gap)
        y = r * (cell + gap)
        svg += f'  <rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="{max(2, cell // 8)}" fill="{col}"/>\n'
    svg += '</svg>\n'
    return svg


def donut_svg(labels, values, size=260):
    """Doughnut-diagram til kanal- og sprogfordeling.

    Returnerer tuple (svg_str, legend_html).
    Brug dem side om side i HTML:
      <div style="display:flex;gap:28px;align-items:center;flex-wrap:wrap">
        <div style="flex-shrink:0">{svg}</div><div>{legend}</div>
      </div>
    OBS: SVG skal have eksplicitte width/height-attributter — ellers kollapser den i flex/grid-layout.
    """
    if not values:
        return '<p>Ingen data</p>', ''
    total = sum(values)
    cx, cy, r, ri = size // 2, size // 2, size // 2 - 10, size // 4
    svg = f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" overflow="visible" xmlns="http://www.w3.org/2000/svg" style="display:block;font-family:sans-serif">\n'
    start = -math.pi / 2
    for i, (lbl, val) in enumerate(zip(labels, values)):
        if val <= 0:
            continue
        col = PALETTE[i % len(PALETTE)]
        if val >= total:
            # Én kategori = hele ringen. En SVG-bue fra et punkt til samme punkt
            # tegnes ikke, så den fulde ring tegnes som en cirkel med tyk streg.
            svg += (f'  <circle cx="{cx}" cy="{cy}" r="{(r + ri) / 2}" fill="none" stroke="{col}" '
                    f'stroke-width="{r - ri}"><title>{_x(lbl)}: {val}</title></circle>\n')
            break
        angle = 2 * math.pi * val / total
        end = start + angle
        x1, y1 = cx + r * math.cos(start), cy + r * math.sin(start)
        x2, y2 = cx + r * math.cos(end),   cy + r * math.sin(end)
        xi1, yi1 = cx + ri * math.cos(start), cy + ri * math.sin(start)
        xi2, yi2 = cx + ri * math.cos(end),   cy + ri * math.sin(end)
        large = 1 if angle > math.pi else 0
        d = f'M{x1:.1f},{y1:.1f} A{r},{r} 0 {large},1 {x2:.1f},{y2:.1f} L{xi2:.1f},{yi2:.1f} A{ri},{ri} 0 {large},0 {xi1:.1f},{yi1:.1f} Z'
        lbl_esc = _x(lbl)
        svg += f'  <path d="{d}" fill="{col}"><title>{lbl_esc}: {val}</title></path>\n'
        start = end
    svg += f'  <text x="{cx}" y="{cy-6}" text-anchor="middle" font-size="24" font-weight="bold" fill="#1e293b">{total}</text>\n'
    svg += f'  <text x="{cx}" y="{cy+14}" text-anchor="middle" font-size="11" fill="#64748b">omtaler</text>\n'
    svg += '</svg>\n'
    legend = '<div style="font-size:13px;line-height:2">'
    for i, (lbl, val) in enumerate(zip(labels, values)):
        col = PALETTE[i % len(PALETTE)]
        pct = round(100 * val / total)
        lbl_esc = _x(lbl)
        legend += (f'<div style="display:flex;align-items:center;gap:8px">'
                   f'<span style="display:inline-block;width:11px;height:11px;background:{col};border-radius:2px;flex-shrink:0"></span>'
                   f'<span>{lbl_esc} <strong>{val}</strong> ({pct}%)</span></div>')
    legend += '</div>'
    return svg, legend
