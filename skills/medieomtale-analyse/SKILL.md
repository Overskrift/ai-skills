---
name: medieomtale-analyse
description: "Brug denne skill når brugeren vil have en analyse eller rapport over medieomtaler fra Overskrift.dk, enten fra en JSON-eksport (felterne `_meta` og `posts`) eller hentet via Overskrifts MCP-værktøjer (list_search_terms, get_media_hits). Trigger når brugeren uploader eller henviser til sådan en fil, eller beder om at analysere medieomtale, presseomtale eller mediedækning af en organisation eller et emne i en periode, fx \"analysér dette\", \"lav en rapport\", \"medieanalyse for uge 40\" eller \"hvad siger medierne om X\". Outputtet er altid en selvstændig HTML-rapport SAMT en PowerPoint-præsentation (.pptx) med de samme nøgletal. Brug den IKKE til eftersyn af søgeprofiler eller til blogindlæg om Overskrift."
---

# Medieomtale-analyse (Overskrift.dk)

Du skal producere en professionel, visuelt rig medieomtaleanalyse som **to filer**:
1. En selvstændig HTML-rapport (ingen eksterne skrifttyper, scripts eller billeder)
2. En PowerPoint-præsentation (.pptx) med de samme nøgletal

Skillen er skrevet til enhver agent der kan køre Python 3.9+ og Node 18+.

## Stier (gælder alle kommandoer nedenfor)

- `SKILL_DIR`: mappen hvor denne SKILL.md ligger. Den kan være skrivebeskyttet
  og deles med andre. **Skriv aldrig filer dertil.**
- `WORK`: en arbejdsmappe du selv opretter til analysen, fx `./medieanalyse-<navn>`.
  Alle input-, mellem- og outputfiler ligger her, og alle kommandoer køres herfra.

```bash
SKILL_DIR=/sti/til/medieomtale-analyse   # tilpas
WORK=./medieanalyse-musik-i-lejet         # tilpas
mkdir -p "$WORK" && cd "$WORK"
npm install --no-save pptxgenjs@^4        # én gang pr. arbejdsmappe (kun til PPTX)
```

Python-scripts bruger kun standardbiblioteket. `render_pptx.js` finder
`pptxgenjs` i arbejdsmappens `node_modules` (eller via `NODE_PATH`).

## Overblik: 5 trin, hvoraf kun ét kræver din dømmekraft

Al beregning og al layout/rendering er **færdigskrevet, testet kode i
`$SKILL_DIR/scripts/`**. Kør den, genskriv den ikke. Det eneste trin der kræver at
du læser og vurderer indhold, er trin 2 (Top 5 mærkesager).

```
Trin 0          Trin 1              Trin 2 (dig)      Trin 3             Trin 4
Hent data  ->   compute_metrics ->  topics.json  ->   resolve_topics ->  render_html + render_pptx
input.json      metrics.json                          topics_resolved
                substantive.json
```

Hvis du er i gang med at skrive en funktion der tæller `groupkey`-værdier,
bygger et SVG-diagram fra bunden eller sætter HTML sammen med f-strings: stop.
Det er løst i `scripts/`. Mangler scriptet noget, så ret det dér.

## Reference-filer (læs kun når du har brug for dem)

- `references/data-format.md`: felterne i input-JSON, `metrics.json`,
  `substantive.json`, `topics.json` og `topics_resolved.json`.
- `references/rendering.md`: rapportens sektioner og slides, waffle-diagrammet,
  oversigt over scripts, og hvordan du retter i skillen.

---

## Trin 0: Hent data til `$WORK/input.json`

**Har brugeren uploadet en eksportfil**, så kopiér den til `input.json`.

**Ellers via Overskrifts MCP-server:**

1. Kald `list_search_terms` og find søgeprofilens `id` ud fra brugerens emne.
   Er flere profiler mulige, så spørg.
2. Omregn perioden til datoer i Europe/Copenhagen. "Uge 40 2026" er ISO-uge 40:
   mandag 28/09 til søndag 04/10-2026. Kald `get_media_hits` med `term`,
   `date_from` og `date_to` (YYYY-MM-DD, begge inklusive).
3. **Brug `_meta.download_url`, hvis du kan hente filer** (kodekørsel/netværk):
   ```bash
   curl -sSf -o input.json "<download_url>"
   ```
   Den indeholder hele resultatet med fulde tekster og er kun gyldig i ca. 15
   minutter, så hent den med det samme. Læs den ikke ind i samtalen.
4. Kun hvis du ikke kan hente filer: kald `get_media_hits` igen med
   `offset=_meta.paging.next_offset`, indtil `has_more` er `false`. Saml alle
   `posts` i én fil med `_meta` fra første svar. Bemærk at `item_desc` her er
   forkortet til 200 tegn, så tema-analysen får et tyndere grundlag. Nævn det
   for brugeren.

Brug aldrig `_meta.period.label` til noget. Den kan afvige fra perioden;
scriptet bruger `period.from`/`to`.

## Trin 1: Beregn metrikker

```bash
python3 "$SKILL_DIR/scripts/compute_metrics.py" input.json --outdir . --org-name "Musik i Lejet"
```

`--org-name` er visningsnavnet i rapportens titel. Udled det fra søgeprofilens
navn eller den første citerede term i søgestrengen, eller spørg hvis det er
tvetydigt.

Scriptet deduplikerer på URL (uden tracking-parametre), samler LinkedIn som én
kilde, fortolker alle tidspunkter i Europe/Copenhagen uanset maskinens
tidszone, og skriver:

- **`metrics.json`**: alle kvantitative nøgletal, klar til rendering.
- **`substantive.json`**: omtaler med tekst nok til tema-analysen. Hvert element
  har `idx`, `title`, `desc`, `src`, `groupkey`, `date_da`, `url`.
  **Det er denne fil du læser i trin 2**, ikke den rå input-JSON.

Valgfrit: `--known-media <liste.json>` udskifter listen over store medier der
bruges til "Fra de største medier". Navne matches på hele ord.

Læs advarsler i scriptets output (fx nye kanaltyper uden dansk navn).

## Trin 2: Identificér Top 5 mærkesager (det eneste kvalitative trin)

Dette er **kvalitativ, semantisk analyse, ikke ordtælling**. Læs
`substantive.json` og find de (op til) 5 mest fremtrædende **temaer,
mærkesager eller holdninger**.

Et tema er IKKE et enkelt ord, men en holdning, et samfundsproblem, en
kampagne eller en diskussion. Fx:
- "Kamp for kortere ventetid til gigtspecialist"
- "Politisk angreb: organisationen kan miste en lovfæstet særret"

For hvert tema:
- `title`: kortfattet navn (3-6 ord)
- `desc`: én sætning om hvad diskussionen handler om
- `post_idx`: **alle** `idx` fra `substantive.json` der handler om temaet. Det
  er grundlaget for tallene i rapporten, så vær grundig. En omtale må gerne stå
  under flere temaer; den tælles kun under det første.
- `example_idx`: 2 repræsentative omtaler, helst fra `post_idx`, og helst nogen
  med en sigende titel (ikke "Instagram tag #...")

```json
{
  "topics": [
    {
      "title": "Kamp for kortere ventetid til gigtspecialist",
      "desc": "Gigtforeningen presser politikerne for maks. 30 dages ventetid og en national gigtplan.",
      "post_idx": [3, 12, 17, 47, 51],
      "example_idx": [12, 47]
    }
  ]
}
```

Rækkefølgen er prioritet (vigtigste først); den bestemmer farve og hvilket tema
en delt omtale tælles under. Omtaler der ikke passer ind i noget tema (fx
falske hits fra søgeprofilen), lader du være; de havner i "Øvrige omtaler".
Ved et lille datasæt er færre end 5 temaer i orden.

**Kun for meget store datasæt**, hvor du ikke realistisk kan klassificere hver
omtale: angiv `"count": <skøn>` i stedet for `post_idx` på alle temaer. Tallene
vises så som "ca." i rapporten, og summen af skøn må ikke overstige det samlede
antal omtaler. Sig til brugeren at tallene er skøn.

Gem som `topics.json`.

## Trin 3: Valider og beregn mærkesagerne

```bash
python3 "$SKILL_DIR/scripts/resolve_topics.py" metrics.json substantive.json topics.json --out topics_resolved.json
```

Scriptet validerer `topics.json` (stopper med en fejlbesked hvis noget er
galt; ret filen og kør igen), tæller hver omtale under ét tema, og beregner
procenter og felter til waffle-diagrammet. Begge render-scripts bruger dette
resultat, så HTML og PPTX viser de samme tal.

## Trin 4: Render output-filerne

```bash
python3 "$SKILL_DIR/scripts/render_html.py" metrics.json topics_resolved.json \
  --logo "$SKILL_DIR/assets/overskrift-logo.svg" --out <navn>-medieanalyse-<periode>.html

node "$SKILL_DIR/scripts/render_pptx.js" metrics.json topics_resolved.json \
  --logo "$SKILL_DIR/assets/overskrift-logo.png" --out <navn>-medieanalyse-<periode>.pptx
```

Begge scripts bygger hele strukturen automatisk. Skal rapporten se anderledes
ud, så ret i scriptene (i skillens kilde) i stedet for at bygge den om ad hoc.

### Filnavngivning

| Søgeterm | Periode | Filnavn (uden endelse) |
|----------|---------|------------------------|
| `Gigtforening*` | maj 2026 | `gigtforeningen-medieanalyse-maj2026` |
| `"Musik i Lejet"` | uge 40 2026 | `musik-i-lejet-medieanalyse-uge40-2026` |

### Tjek før du afleverer

- Kør begge render-scripts uden fejl, og åbn/se HTML-filen.
- Antallet af dage i KPI'en svarer til den bestilte periode.
- Fortæl brugeren om advarsler fra scripts (fx skøn i stedet for optælling,
  forkortede tekster fra paging eller falske hits i søgeprofilen).

---

## Tone og sprog

- Al tekst i outputfilerne er på **dansk**, inklusive `title`/`desc` i `topics.json`.
- Professionel men tilgængelig tone: rapporten skal kunne læses af en
  kommunikationschef der ikke er datafaglig.
- Undgå jargon, og forklar hvad tallene betyder i praksis.
- Brug ikke tankestreger (—) i teksterne; brug komma, kolon eller punktum.
