# Changelog: medieomtale-analyse

## 2.0 (2026-10-05)

Pipelinen har fået et nyt trin og et nyt `topics.json`-format. Kørsler med den
gamle opskrift fejler med en tydelig besked i stedet for at give forkerte tal.

### Ændret workflow
- Nyt trin 3: `resolve_topics.py` validerer `topics.json`, tæller omtaler pr.
  tema og beregner procenter, felter og farver. Begge render-scripts læser nu
  `topics_resolved.json` (`render_html.py` tager ikke længere `substantive.json`).
- `topics.json` angiver `post_idx` (alle omtaler pr. tema) i stedet for et skønnet
  `count`. Overlap mellem temaer håndteres: en omtale tælles under det første tema.
  `count` er fortsat muligt som skøn for meget store datasæt og vises som "ca.".
- SKILL.md beskriver datahentning via Overskrifts MCP (`download_url` frem for
  paging), faste stier (`SKILL_DIR`/`WORK`), og at intet må skrives i skill-mappen.
- Teksten er agent-neutral (virker for Claude, Codex m.fl.).

### Rettede fejl, der gav forkerte tal
- Antal dage og gennemsnit pr. dag kom fra `_meta.period.label`, som kan være
  forkert (uge 40 gav "6 dage"). Beregnes nu fra `period.from/to`.
- Tidspunkter blev fortolket i maskinens tidszone. I UTC-sandkasser rykkede
  periode og omtaler til forkert dag. Bruger nu `_meta.period.timezone`
  (default Europe/Copenhagen).
- `<mark>`-tags blev erstattet med mellemrum ("Musik i Leje t").
- "Mest markante medier" matchede på delstrenge ("DR" ramte "Andreas",
  "Information" ramte "Turistinformation") og valgte bare de nyeste. Matcher nu
  hele ord og prioriterer artikler hvor emnet står i titlen.
- "Foto/Video fra ..."-opslag blev frasorteret uanset tekstlængde, så relevante
  opslag aldrig nåede tema-analysen.
- Dedup ignorerede tracking-parametre (`?referrer=RSS`, `utm_*`), så samme
  artikel kunne tælle to gange.
- LinkedIn-afsendere blev ikke samlet til én kilde.
- Tidslinjen dækkede kun dagene mellem første og sidste omtale; nu hele perioden.
  Time-granularitet sprang tomme timer over og viste ikke datoen.
- Y-aksen viste "0, 0, 0, 0, 1" ved små tal; rundes nu op til pæne heltal.

### Rettede fejl i rendering og robusthed
- Donut med kun én kanal blev usynlig.
- URL'er blev ikke escapet i attributter, og `javascript:`-links blev ikke afvist.
- HTML hentede Google Fonts; nu helt selvstændig og offline-sikker.
- PPTX-slide med udvalgte omtaler kunne stå tom og havde ingen links.
- `render_pptx.js` krævede `npm install` i skill-mappen; finder nu pakken i
  arbejdsmappen og giver en klar fejl hvis den mangler. Skrivefejl giver exit 1.
- `--outdir` oprettes hvis den mangler; default er inputfilens mappe.
- Alle HTML-entiteter afkodes (`html.unescape`).
- Gennemsnit vises med dansk komma; søgetermen får ikke dobbelte anførselstegn
  i PPTX; tankestreger er fjernet fra rapportteksterne.
