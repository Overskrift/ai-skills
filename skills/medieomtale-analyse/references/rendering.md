# Rendering: layout, waffle-diagram og scripts

## Indhold
- Rapportens struktur (HTML-sektioner og PPTX-slides)
- Top 5 mærkesager som waffle-diagram
- Fordeling på præcis 100 felter
- Oversigt over `scripts/` og `assets/`
- Sådan retter du i skillen

Læs denne fil hvis rapporten skal se anderledes ud, hvis et render-script
fejler, eller hvis et nyt datasæt afslører en grænsesag. Ved en normal kørsel
er den ikke nødvendig.

---

## Rapportens struktur

**HTML** (`render_html.py`) bygger sektionerne i denne rækkefølge:

`Header → KPI-kort → Tidslinje → Kanalfordeling → Top 10 kilder →
Top 5 mærkesager → (Sprogfordeling, hvis relevant) → Udvalgte omtaler → Footer`

HTML-filen er helt selvstændig: systemskrifttyper, inline SVG og inline logo.
Den henter intet udefra, virker offline og sender ikke læserens IP-adresse
til tredjepart. Alle links er begrænset til http(s), og al tekst fra data
escapes, også i attributter.

"Udvalgte omtaler" viser de 5 seneste og op til 5 fra de største medier. Er
der ingen fra de største medier, står der det i stedet.

**PPTX** (`render_pptx.js`) har 7 faste slides: titel, KPI, tidslinje,
kanalfordeling, top 10 kilder, mærkesager, udvalgte omtaler. Der er **ingen
separat afslutningsslide**. Overskrift-logoet sidder i nederste højre hjørne
af den sidste slide. Titlerne på udvalgte omtaler er klikbare links. Er der
ingen omtaler fra de største medier, viser sliden de seneste omtaler.

---

## Top 5 mærkesager: waffle-diagram

Top 5-sektionen i både HTML og PPTX er et **waffle-/piktogram-diagram**: et fast
gitter på 100 felter (altid 10×10), hvor hvert felt svarer til 1 % af
`metrics.json`'s `total`. De op til 5 temaer får hver deres farve fra
`PALETTE`, og alt der ikke er dækket af temaerne samles i en grå kategori,
"Øvrige omtaler". Gitteret summer altså til hele datasættet.

Et waffle-diagram forudsætter at kategorierne ikke overlapper. Derfor tæller
`resolve_topics.py` hver omtale under det første (vigtigste) tema den står i,
og viser "berører N" når flere omtaler berører temaet end der er talt under det.

Formen er valgt frem for et kagediagram, fordi top 5 ofte kun dækker 15-25 %
af alle omtaler. I en donut bliver "øvrige"-skiven så stor, at de fem temaer
bliver til tynde, svært sammenlignelige kiler. Kanal- og sprogfordeling bruger
fortsat donut (`donut_svg`), fordi de kategorier naturligt summerer til 100 %.

## Fordeling på præcis 100 felter

Rund aldrig selv hver andel til nærmeste hele felt; det kan summe til 97 eller
103 og ødelægge gitteret. `resolve_topics.py` bruger `apportion_squares()` fra
`svg_helpers.py` ("largest remainder"), som garanterer præcis 100 felter og
mindst ét felt til ethvert tema med omtaler. Render-scripts tegner bare de
felter der står i `topics_resolved.json`, så HTML og PPTX altid er ens.

---

## Oversigt over `scripts/` og `assets/`

| Fil | Rolle | Afhængigheder |
|-----|-------|---------------|
| `scripts/compute_metrics.py` | Trin 1: dedup, nøgletal, `metrics.json` + `substantive.json` | Python 3.9+, standardbibliotek |
| `scripts/resolve_topics.py` | Trin 3: validerer `topics.json`, tæller, beregner felter og farver | Standardbibliotek, `svg_helpers.py` |
| `scripts/render_html.py` | Trin 4: HTML-rapport | Standardbibliotek, `svg_helpers.py` |
| `scripts/render_pptx.js` | Trin 4: PPTX | Node 18+, `pptxgenjs` (installeres i arbejdsmappen) |
| `scripts/svg_helpers.py` | SVG-primitiver, `PALETTE`, `apportion_squares` | Standardbibliotek |
| `assets/overskrift-logo.svg` | Logo til HTML-footeren | |
| `assets/overskrift-logo.png` | Samme logo prærenderet til PPTX | |

Funktioner i `svg_helpers.py`:

- `PALETTE`: farveliste. Temafarver kommer herfra via `topics_resolved.json`;
  `render_pptx.js` har sin egen kopi til kanalfordelingen (hold dem synkrone)
- `fmt_num`, `fmt_xlabel`: talformatering og akselabels
- `hbar_svg`: vandrette søjler (top kilder)
- `vbar_svg`: lodrette søjler med glidende gennemsnit (tidslinje); aksen rundes
  op til pæne heltal
- `donut_svg`: donut (kanal- og sprogfordeling); returnerer `(svg, legend_html)`,
  og tegner en hel ring når der kun er én kategori
- `apportion_squares`: largest remainder-fordeling på 100 felter
- `waffle_svg`: 10×10 waffle-gitter (mærkesager)

---

## Sådan retter du i skillen

Ret i skillens **kilde** (ikke i en synkroniseret eller skrivebeskyttet kopi),
og lad ændringen blive i skillen i stedet for at patche den enkelte analyse.

- Andet layout, andre farver, ekstra sektion: `render_html.py`,
  `render_pptx.js` eller `svg_helpers.py`.
- Ændres `PALETTE`, så ret både `svg_helpers.py` og `render_pptx.js`.
- Nyt kanal-navn uden dansk oversættelse: `GK_TRANSLATE` i `compute_metrics.py`.
- Flere eller andre "største medier": `DEFAULT_KNOWN_MEDIA` i
  `compute_metrics.py`, eller `--known-media` for en enkelt analyse.
- Tilføj en linje i `CHANGELOG.md`.
