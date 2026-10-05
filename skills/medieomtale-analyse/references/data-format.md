# Dataformater: input-JSON og mellemfiler

## Indhold
- Input: `_meta` (metadata om eksporten)
- Input: `posts[]` (de enkelte omtaler) og deduplikering
- Output fra trin 1: `metrics.json`
- Output fra trin 1: `substantive.json`
- Input til trin 3: `topics.json` (skrevet af agenten)
- Output fra trin 3: `topics_resolved.json`

Læs denne fil hvis input-JSON'en ser anderledes ud end forventet, hvis
`compute_metrics.py` fejler på et felt, eller hvis du skal rette i scriptet.
Ved en normal kørsel er den ikke nødvendig.

---

## Input: `_meta`

Filen fra Overskrift.dk har altid to hoveddele: `_meta` og `posts`.

| Felt | Beskrivelse |
|------|-------------|
| `_meta.source` | Altid "Overskrift.dk" |
| `_meta.query.searchterm` | Den anvendte søgestreng (wildcards, quotes, boolske operatorer) |
| `_meta.period.from` / `.to` | Perioden som Unix timestamps (fra-start til til-slut, begge inklusive) |
| `_meta.period.timezone` | Periodens tidszone, fx "Europe/Copenhagen". Alle datoer fortolkes i den |
| `_meta.period.label` | Menneskelig periodelabel, fx "30 dage". **Bruges ikke**: den kan afvige fra from/to |
| `_meta.counts.total` | Antal omtaler i eksporten. I et MCP-svar: antal i DETTE svar (én side) |
| `_meta.download_url` | (kun MCP) Link til hele resultatet som én fil med fulde tekster, gyldigt ca. 15 min. |
| `_meta.paging` | (kun MCP) `has_more`, `next_offset` til at hente næste side |

## Input: `posts[]`

| Felt | Beskrivelse |
|------|-------------|
| `item_url` | URL til det originale opslag |
| `item_title` | Titel på artikel/opslag. Kan indeholde `<mark>`-tags fra søge-highlight, også midt i et ord |
| `item_desc` | Brødtekst eller uddrag (kan indeholde HTML og entiteter; forkortet til 200 tegn i MCP-sider) |
| `item_summary` | (kun MCP) Uddrag omkring første match, med `<mark>`-tags |
| `item_date` | Unix timestamp (sekunder) for publicering. Det er dette felt scripts bruger |
| `pubdate` | Lokal datostreng (YYYY-MM-DD HH:MM); kun til visning |
| `groupkey` | Kanaltype: `websites`, `facebook`, `linkedin`, `twitter`, `bluesky`, `instagram`, `reddit`, `podcast`, `blogs`, `youtube`, `trustpilot` m.fl. |
| `title` | Kildenavn, fx "Politiken.dk", "Berlingske" eller "Facebooksiden X" |
| `siteurl` | URL til kildens forside |
| `searchterm` | Den søgeterm der matchede dette opslag |
| `language` | Sprogkode, hvis kendt (kan være strengen "None") |
| `author` | Afsender på sociale medier, hvis kendt |

Samme artikel kan optræde flere gange, fx hvis den matcher flere søgetermer
eller findes både med og uden tracking-parametre (`?referrer=RSS`, `utm_*`).
Derfor deduplikerer `compute_metrics.py` på URL uden tracking-parametre og
fragment som første skridt, og beholder versionen med længst tekst.

LinkedIn-opslag har forskellige kildenavne pr. afsender. De samles som én
kilde, "LinkedIn", før alle statistikker beregnes.

Et nyt `groupkey` uden dansk oversættelse skal tilføjes i `compute_metrics.py`,
ikke patches i den enkelte analyse.

---

## Output: `metrics.json`

Alle kvantitative nøgletal, klar til rendering:

- `org_name`, `searchterm_display`, `period_label_da`, `n_days`, `generated_date_da`
- `total` (efter dedup), `duplicates_removed`, `avg_per_day`, `unique_sources`, `unique_channels`
- `n_days` beregnes fra `_meta.period.from/to` i periodens tidszone
- `timeline`: labels, values, glidende gennemsnit (`ma`) og top 3-indeks.
  Dækker hele perioden, også tomme dage. Granularitet vælges efter periodens
  længde: time (op til 3 dage, labels "28/09 14h"), dag (op til 60), uge (op
  til ca. 6 måneder, mandag som ugestart), måned
- `channels`: kanalfordeling med dansk-oversatte labels
- `top_sources`: top kilder med `siteurl`
- `language_share` + `language_distribution`: sprogfordeling, kun udfyldt hvis
  over 30% af omtalerne har sprog-data
- `newest5`: de fem nyeste omtaler
- `notable5`: op til 5 omtaler fra store medier (`--known-media`, matches på
  hele ord). Omtaler hvor emnet står i titlen og artikler fra nyhedssites
  prioriteres før nyeste dato. Kan være tom.

Alle datoer er formateret dansk (`DD/MM-YYYY`).

## Output: `substantive.json`

De omtaler der er substantielle nok til tema-analysen i trin 2. Opslag på
Instagram/Facebook og "Foto/Video fra ..."-opslag med under 40 tegns tekst er
frasorteret. Det afgøres af teksten, ikke af titlen.

Hvert element har:

| Felt | Beskrivelse |
|------|-------------|
| `idx` | Løbenummer, bruges i `topics.json` som `example_idx` |
| `title` | Titel på omtalen |
| `desc` | Brødtekst/uddrag |
| `src` | Kildenavn |
| `groupkey` | Kanaltype |
| `date_da` | Dato i dansk format |
| `url` | Link til omtalen |

---

## `topics.json` (agentens tema-analyse, trin 2)

Foretrukket format med optælling:

| Felt | Beskrivelse |
|------|-------------|
| `title` | Temaets navn, 3-6 ord |
| `desc` | Én sætning om temaet |
| `post_idx` | Alle `idx` fra `substantive.json` der handler om temaet |
| `example_idx` | 2 repræsentative `idx` (default: de 2 første i `post_idx`) |

Fallback for meget store datasæt: `count` (heltal, skøn) i stedet for
`post_idx`, på alle temaer. Blandes de to formater, stopper `resolve_topics.py`.

## `topics_resolved.json` (trin 3, input til begge render-scripts)

- `estimated`: `true` hvis tallene er skøn (`count`-formatet)
- `total`: antal omtaler i alt
- `topics[]`: `title`, `desc`, `color`, `count` (omtaler talt under dette tema),
  `count_touching` (alle omtaler der berører temaet), `pct` (af `total`),
  `squares` (felter i 10x10-gitteret), `examples[]` (`title`, `src`, `url`, `date_da`)
- `rest`: samme felter for "Øvrige omtaler"
- `note`: forklaring der vises under overskriften i rapporten

Summen af alle `squares` er altid præcis 100.
