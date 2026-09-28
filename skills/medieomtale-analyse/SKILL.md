---
name: medieomtale-analyse
description: >
  Brug denne skill når brugeren vil have en analyse af medieomtaler fra Overskrift.dk.
  Trigger når brugeren uploader eller refererer til en JSON-fil med medieomtaler, mediedata
  eller mediemonitorering — også selvom de bare siger "analysér dette", "lav en rapport" eller
  "hvad siger medierne om X". Filen indeholder typisk felterne `_meta` og `posts`.
  Outputtet er altid en selvstændig, interaktiv HTML-fil med visuelle grafer og tabeller,
  SAMT en PowerPoint-præsentation (.pptx) med de samme nøgletal.
  Brug også denne skill hvis brugeren blot nævner "Overskrift.dk", "medieomtaler",
  "presseomtale", "mediedækning" eller "medieovervågning".
---

# Medieomtale-analyse (Overskrift.dk JSON)

Du skal producere en professionel, visuelt rig medieomtaleanalyse som **to filer**:
1. En selvstændig HTML-fil med interaktive grafer
2. En PowerPoint-præsentation (.pptx) med de samme nøgletal

## Sådan virker skillen: 3 trin, hvoraf kun ét kræver din dømmekraft

Al beregning og al layout/rendering er **færdigskrevet, testet kode i `scripts/`**.
Kør den — genskriv den ikke. Det eneste trin der reelt kræver at du læser og
vurderer indhold, er trin 2 (Top 5 mærkesager). Trin 1 og 3 er ren scriptkørsel.

```
Trin 1 (script)     Trin 2 (dig)                Trin 3 (script)
─────────────       ──────────────────          ──────────────────
compute_metrics.py  Læs substantive.json         render_html.py
  → metrics.json     Skriv topics.json           render_pptx.js
  → substantive.json (kvalitativ tema-analyse)     → .html + .pptx
```

Hvis du bemærker dig selv i gang med at skrive en Python-funktion der tæller
`groupkey`-værdier, bygger et SVG-søjlediagram fra bunden, eller sætter en
lang HTML/CSS-streng sammen med f-strings — stop. Det er allerede løst i
`scripts/`. Brug scriptet i stedet, eller sig til hvis det rent faktisk
mangler noget, så det kan rettes i scriptet fremover i stedet for at blive
løst ad hoc igen.

---

## JSON-formatets struktur

Filen fra Overskrift.dk har altid to hoveddele:

### `_meta` — metadata om eksporten

| Felt | Beskrivelse |
|------|-------------|
| `_meta.source` | Altid "Overskrift.dk" |
| `_meta.query.searchterm` | Den anvendte søgestreng (wildcards, quotes, boolske operatorer) |
| `_meta.period.from` / `.to` | Perioden som Unix timestamps |
| `_meta.period.label` | Menneskelig periodelabel, fx "30 dage" |
| `_meta.counts.total` | Samlet antal omtaler i eksporten |

### `posts[]` — de enkelte omtaler

| Felt | Beskrivelse |
|------|-------------|
| `item_url` | URL til det originale opslag |
| `item_title` | Titel på artikel/opslag |
| `item_desc` | Brødtekst eller uddrag (~500 tegn, kan indeholde HTML-entiteter) |
| `item_date` | Unix timestamp (sekunder) for publicering |
| `pubdate` | Publiceringstidspunkt som lokal datostreng (YYYY-MM-DD HH:MM:SS) |
| `groupkey` | Kanaltype: `websites`, `facebook`, `linkedin`, `twitter`, `bluesky`, `instagram`, `reddit`, `podcast`, `blogs`, `youtube`, `trustpilot` m.fl. |
| `title` | Kildenavn, fx "Politiken.dk", "Berlingske" eller "Facebooksiden X" |
| `siteurl` | URL til kildens forside |
| `searchterm` | Den søgeterm der matchede dette opslag |

Samme artikel kan optræde flere gange hvis den matcher flere søgetermer — derfor
deduplikerer `compute_metrics.py` altid på `item_url` som første skridt.

---

## Trin 1: Beregn metrikker (`scripts/compute_metrics.py`)

Ingen ekstra Python-pakker kræves — kun standardbiblioteket.

```bash
python3 scripts/compute_metrics.py <input.json> --outdir <arbejdsmappe> --org-name "Danmarks Naturfredningsforening"
```

`--org-name` er visningsnavnet i rapportens titel/header. Udled det fra den
første citerede term i søgestrengen, eller spørg brugeren hvis det er
tvetydigt (fx flere lige centrale navne i søgetermen). Uden `--org-name`
gætter scriptet selv ud fra `_meta.query.searchterm`.

Scriptet gør **alt** det mekaniske arbejde og skriver to filer:

**`metrics.json`** — alle kvantitative nøgletal, klar til rendering:
`org_name`, `searchterm_display`, `period_label_da`, `n_days`, `total`,
`avg_per_day`, `unique_sources`, `unique_channels`, `timeline` (labels,
values, glidende gennemsnit, top 3-indeks — granularitet vælges automatisk
efter periodens længde: time/dag/uge/måned), `channels` (dansk-oversatte
labels), `top_sources` (med `siteurl`), `language_share` +
`language_distribution` (kun udfyldt hvis >30% har sprog-data),
`newest5`, `notable5` (kendte medier — se `--known-media` nedenfor),
`generated_date_da`.

**`substantive.json`** — de omtaler der er "substantielle nok" til at indgå i
tema-analysen (fotoposts og indholdsløse Instagram/Facebook-opslag er
frasorteret). Hvert element har et `idx`, samt `title`, `desc`, `src`,
`groupkey`, `date_da`, `url`. **Det er denne fil du læser i trin 2** — ikke
den rå input-JSON, som ofte er for stor til at læse i sin helhed på én gang.

Valgfrit: `--known-media <sti.json>` peger på en JSON-liste af medienavne der
definerer "mest markante" i `notable5` (default er en indbygget liste over
store danske medier — udvid kun hvis en tydeligvis kendt kilde mangler).

Alle datoer i output er allerede formateret dansk (`DD/MM-YYYY`) — konvertér
ikke selv.

---

## Trin 2: Identificér Top 5 mærkesager (det eneste kvalitative trin)

Dette er **kvalitativ, semantisk analyse — ikke ordtælling**, og er grunden
til at et menneske (eller en LLM) skal involveres frem for endnu et script.

Læs `substantive.json` og identificér de 5 mest fremtrædende **temaer,
mærkesager eller holdninger** der går igen i `title`+`desc`.

Et tema er IKKE et enkelt ord — det er en beskrivelse af en holdning, et
samfundsproblem, en kampagne eller en diskussion. Eksempler:
- "Kamp for kortere ventetid til gigtspecialist"
- "Politisk angreb: organisationen kan miste en lovfæstet særret"
- "Historisk millionunderskud vælter ind over landets medier"

For hvert tema:
- Giv det et kortfattet navn (3-6 ord)
- Skriv en sætning der forklarer hvad diskussionen handler om
- Find 2 repræsentative posts som eksempler — brug deres `idx` fra `substantive.json`
- Angiv et skøn over hvor mange substantielle posts der berører temaet

Skriv resultatet til `topics.json` i **præcis** dette format (bruges direkte
af render-scripts i trin 3):

```json
{
  "topics": [
    {
      "title": "Kamp for kortere ventetid til gigtspecialist",
      "desc": "Gigtforeningen presser politikerne for maks. 30 dages ventetid og en national gigtplan.",
      "count": 38,
      "example_idx": [12, 47]
    }
  ]
}
```

Præcis 5 temaer, i faldende prioritet (vigtigste først — det bestemmer
rækkefølgen og farven i output). `count` skal være dit skøn over antal
substantielle posts der berører temaet — render-scripts beregner selv hver
mærkesags andel af `metrics.json`'s `total` (dvs. af **samtlige** omtaler i
perioden, ikke kun af summen af de 5 temaer).

### Sådan vises Top 5 mærkesager: waffle-diagram

Top 5-sektionen i både HTML og PPTX er et **waffle-/piktogram-diagram**: et
fast gitter på 100 felter (altid 10×10, aldrig mere eller færre rækker), hvor
hvert felt svarer til 1% af `metrics.json`'s `total`. De 5 temaer får hver
deres farve fra `PALETTE`, og alt der ikke er dækket af de 5 temaer samles i
en 6. — grå — kategori, "Øvrige omtaler", så gitteret altid summer til hele
datasættet i stedet for kun til top-5-summen.

Denne form er bevidst valgt frem for et kagediagram: når top 5 kun dækker en
mindre del af det samlede antal omtaler (helt normalt — ofte 15-25%), bliver
en "øvrige"-skive i en donut meget stor, og de fem reelle temaer bliver til
tynde, svært sammenlignelige kileudsnit i periferien. I et waffle-gitter kan
man i stedet tælle og sammenligne felter direkte.

**Rund aldrig selv hver mærkesags andel til nærmeste hele felt** — det kan
sagtens summe til fx 87 eller 103 felter og ødelægge det faste 10×10-gitter.
Brug altid `apportion_squares()` (Python, i `svg_helpers.py`) eller
`apportionSquares()` (JS, i `render_pptx.js`), som bruger "largest
remainder"-metoden til at garantere at fordelingen summer til **nøjagtig**
100 felter, uanset hvordan de enkelte procentandele runder af. Begge scripts
kalder allerede denne funktion — det er kun relevant at kende til, hvis du
selv skal rette i render-koden.

---

## Trin 3: Render output-filerne (`scripts/render_html.py` + `scripts/render_pptx.js`)

```bash
python3 scripts/render_html.py metrics.json substantive.json topics.json \
  --logo assets/overskrift-logo.svg --out <navn>-medieanalyse-<måned><år>.html

node scripts/render_pptx.js metrics.json topics.json \
  --logo assets/overskrift-logo.png --out <navn>-medieanalyse-<måned><år>.pptx
```

`render_pptx.js` kræver `pptxgenjs` (`npm install pptxgenjs` — kør én gang pr.
session/miljø hvis `node_modules` ikke allerede findes). Intet andet
run-time-afhængighed: logoet ligger allerede som PNG i `assets/`, så der er
**ikke** brug for `cairosvg`-konvertering længere.

Begge scripts bygger den fulde struktur automatisk:
`Header → KPI-kort → Tidslinje → Kanalfordeling → Top 10 kilder →
Top 5 mærkesager → (Sprogfordeling, hvis relevant) → Udvalgte omtaler → Footer`
og PPTX'ens 7 faste slides (titel, KPI, tidslinje, kanalfordeling, top 10
kilder, mærkesager, udvalgte omtaler — **ingen separat afslutningsslide**,
Overskrift-logoet sidder i stedet i nederste højre hjørne af den sidste
slide).

Hvis rapporten skal se anderledes ud — andet layout, andre farver, ekstra
sektion — så ret i `render_html.py`/`render_pptx.js`/`svg_helpers.py` og lad
ændringen blive i skillen, i stedet for at bygge den om ved siden af hver
gang. Det er hele pointen med at have scriptene.

---

## Eksempel på filnavngivning

| Søgeterm | HTML-filnavn | PPTX-filnavn |
|----------|-------------|--------------|
| `Gigtforening*` | `gigtforeningen-medieanalyse-maj2026.html` | `gigtforeningen-medieanalyse-maj2026.pptx` |
| `"Musik i Lejet"` | `musik-i-lejet-medieanalyse-maj2026.html` | `musik-i-lejet-medieanalyse-maj2026.pptx` |

---

## Tone og sprog

- Skriv al tekst i outputfilerne på **dansk** (temaernes `title`/`desc` i `topics.json` inklusive)
- Professionel men tilgængelig tone — rapporten skal kunne læses af en kommunikationschef
  der ikke er datafaglig
- Undgå jargon — forklar hvad tallene betyder i praksis

---

## Reference: hvad ligger i `scripts/` og `assets/`

- `scripts/compute_metrics.py` — trin 1, se ovenfor. Ingen eksterne afhængigheder.
- `scripts/render_html.py` — trin 3 (HTML). Importerer `svg_helpers.py`. Ingen eksterne afhængigheder.
- `scripts/render_pptx.js` — trin 3 (PPTX). Kræver `pptxgenjs` (npm).
- `scripts/svg_helpers.py` — SVG-chart-primitiver (`hbar_svg`, `vbar_svg`, `donut_svg`, `fmt_num`,
  `fmt_xlabel`, `PALETTE`) brugt internt af `render_html.py`. Skal normalt ikke kaldes direkte.
- `assets/overskrift-logo.svg` — logo til HTML-footeren.
- `assets/overskrift-logo.png` — samme logo, prærenderet til PPTX (undgår cairosvg-afhængighed).

Hvis et fremtidigt datasæt afslører et nyt behov (nyt kanal-navn der mangler
dansk oversættelse, en periodelængde der rammer en grænsesag i
granularitets-logikken, etc.), så ret det i `compute_metrics.py` frem for at
patche det ad hoc i den enkelte analyse — så virker rettelsen automatisk
næste gang også.
