---
name: overskrift-soegeprofil-audit
description: "Brug denne skill når brugeren vil have et eftersyn, audit, kvalitetstjek eller review af en søgeprofil i Overskrift.dk, eller spørger om en søgning er god nok, rammer rigtigt, larmer eller mangler noget. Trigger på profilnavn plus ord som audit, eftersyn, kvalitet, støj, falske hits, dækning, forbedre søgestreng."
---

# Audit af Overskrift-søgeprofil

Et eftersyn af en søgeprofil svarer på tre spørgsmål: er søgestrengen teknisk korrekt, rammer den det den skal, og mangler den noget. Output er en rapport i chatten. Ingen filer, medmindre brugeren beder om det.

Denne version er optimeret til lavere tokenforbrug end tidligere: kompakt stikprøvevisning uden fast kolonnebredde, en mindre standard-stikprøve, en `inspect`-kommando til at slå enkelte hits op i stedet for ad hoc-kode, og et eksplicit tjek før scriptet skrives. Metoden og konklusionerne er uændrede, kun mængden af tekst der føres gennem samtalen er skåret ned.

## Sprogbrug over for kunder

Denne skill bruges af Overskrifts kunder, som arbejder med medieovervågning og ikke med søgeteknologi. Rapporten skal kunne læses uden kendskab til, hvad der ligger bag en søgning. Skriv derfor funktionelt og konkret.

**Undlad teknologinavne.** Nævn ikke navne på databaser, søgemaskiner, indekseringsmotorer, biblioteker, analyzere, tokenizers, query-sprog eller leverandører, hverken i rapporten, i mellemregninger eller i forslag til brugeren. Skriv heller ikke "det virker som i <produkt>" eller "svarer til <produkts> syntaks". Navnene siger ikke brugerne noget og leder opmærksomheden væk fra det, de skal bruge rapporten til: at vurdere om søgningen rammer rigtigt. Skillen beskriver desuden kun, hvordan søgningen opfører sig i data, ikke hvordan den er bygget.

Beskriv i stedet adfærd funktionelt og observeret:

| Skriv ikke | Skriv i stedet |
|---|---|
| "<produkt> splitter på bindestreg" | "søgningen ser ud til at behandle bindestreg som ordadskiller" |
| "indekset er bygget på <produkt>" | "Overskrifts indeks over medieomtaler" |
| "analyzeren stemmer ikke ejefald" | "ejefaldsformen bliver ikke fanget af frasen" |

Når du udleder noget om, hvordan søgningen opfører sig, så præsentér det som en observation fra data plus en test, brugeren kan køre, ikke som viden om et bestemt produkt. Spørger brugeren, hvad der ligger bag, så svar at skillen beskriver søgningens adfærd og ikke den tekniske opbygning, og at spørgsmål om platformen kan rettes til Overskrift.

Id'er på søgninger og hits har heller ingen betydning for en kunde. Brug søgetitler, søgetermer og titler og indhold fra resultater, men ikke id'er.


## Søgesyntaks i Overskrift

Søgestrengen er en boolsk søgning mod Overskrifts indeks over medieomtaler. Der skelnes ikke mellem store og små bogstaver.

| Element | Betydning |
|---|---|
| `ord ord2` | Mellemrum er OR. Et hit skal matche mindst ét udtryk |
| `"flere ord"` | Frase, matcher ordene i rækkefølge |
| `"a b"~4` | Nærhedssøgning, a og b inden for 4 ord |
| `stamme*` | Wildcard-suffiks, kun i slutningen af en term |
| `+term` | Obligatorisk, skal forekomme |
| `-term` | Stopord, udelukker hittet |
| `(a b)` | Gruppe uden operator: en sideordnet OR-gren på linje med de øvrige udtryk |
| `(+a +b)` | Gruppe der kræver både a og b, men kun inden for grenen. Grenen selv er sideordnet |
| `+(a b)` | Gruppen er obligatorisk, og inden i den er a og b sideordnede |
| `-(a b)` | Stopordsgruppe, udelukker hits med a eller b |

**Operatorernes rækkevidde.** Det her er den hyppigste kilde til fejllæsning, så vær præcis:

- Et `+` på topniveau er et krav til hele søgningen. Står der `A B +C`, kommer der kun hits med C, og A og B udvider ikke resultatsættet.
- Et `+` inde i en gruppe uden egen operator er kun et krav inden for den gruppe. `A B C (+x +y)` betyder A eller B eller C eller (x og y). De frie termer virker uafhængigt af x og y.

En søgestreng med `(+x +y)` er altså helt normal opsat, ikke en fejl. Konkludér aldrig, at frie termer er sat ud af kraft, uden at have målt det: tjek om der findes hits der matcher en fri term uden at opfylde kravene i gruppen. Findes de, virker de frie termer.

**En hyppig og alvorlig fejl, både at finde i eksisterende profiler og selv at undgå når du foreslår en ny streng**: `+` skal stå direkte foran hvert enkelt obligatorisk led, ikke foran en parentes der blander et frit og et obligatorisk led. `+(A +(B C))` betyder IKKE "A og (B eller C)". Det betyder at hele parentesen er obligatorisk som gren i den ydre søgning, men internt i parentesen er `A` og `+(B C)` to sideordnede OR-alternativer uden nogen reel binding mellem dem. Resultatet er at `A` alene er tilstrækkeligt, og at `B` eller `C` alene ligeledes er tilstrækkeligt, uafhængigt af hinanden, stik imod hensigten. Den korrekte struktur for "A og (B eller C)" som én gren i en større søgning er `(+A +(B C))`: ingen `+` foran selve den ydre parentes, men et `+` foran hvert af de to led der reelt skal opfyldes sammen. Denne fejl er særlig farlig fordi den ikke giver en lint-fejl eller advarsel, den ser syntaktisk gyldig ud. Test den derfor altid empirisk i trin 6, både når du reviderer en eksisterende streng og når du selv forfatter en ny: tjek at det tiltænkte hovedudtryk (A) reelt optræder i praktisk talt alle hits fra den gren, ikke kun i nogle. Optræder det ikke i næsten alle, er grenen sandsynligvis blevet en fri OR i stedet for et AND-krav. Skriv aldrig et forslag til en ny eller revideret søgestreng uden selv at have kørt `expansions` og `attribute` på strengen (eller en tilstrækkelig del af den) og bekræftet mønstret, en visuel gennemlæsning er ikke nok, denne fejl er nem at overse selv ved omhyggelig korrekturlæsning.

**Bredt anvendte, polyseme danske ord er farlige som kontekstled i en `+`-gruppe.** Ord som `nøgle*`, `kæde*`, `adgang*`, `sikkerh*` og `salto*` optræder i almindeligt dansk sprogbrug i betydninger der intet har med den overvågede virksomhed at gøre: `nøgle*` fanger `nøgleord`, `nøgletal` og `nøglefigur`, `kæde*` fanger `kædedirektør` og enhver anden omtale af en butikskæde, `adgang*` og `sikkerh*` er almindelige ord i enhver kommunal dagsorden eller nyhedsartikel. Et krav som `+Abus +(nøgle* kæde*)` beskytter ikke fuldt ud mod dette, for `+` i Overskrift virker på hele dokumentet, ikke på sætnings- eller afsnitsnærhed. En lang artikel eller en samleside kan sagtens nævne Abus ét sted og "nøgleordet" et helt andet sted uden sammenhæng, og hittet tælles alligevel med. Foretræk derfor specifikke sammensætninger frem for de brede rødder, fx `nøgleboks*` i stedet for `nøgle*`, `kædelås*` i stedet for `kæde*`, `adgangskontrol*` i stedet for `adgang*`, `sikringsanlæg*` i stedet for `sikkerh*`. Nævn altid i rapporten, når en revideret streng stadig bruger et bredt ord som kontekst, at `+` ikke garanterer nærhed, og at en test af det faktiske antal hits i Overskrift derfor er nødvendig før strengen gemmes, uanset hvor fornuftig strukturen ser ud på papiret.

Konvention hos brugeren: personnavne i anførselstegn sættes altid op med ejefaldsvariant ved siden af grundformen, fx `"Hans Peter Hansen" "Hans Peter Hansens"`. Samme konvention gælder stopord: et stopord i én form fanger ikke nødvendigvis ejefald eller sammenskrivning.

## Arbejdsgang

Al deterministisk logik ligger i scriptet i afsnittet **Script**, som har syv kommandoer: `lint`, `prepare`, `expansions`, `sample`, `mark`, `inspect` og `attribute`. Skriv aldrig ad hoc-kode til parsing, optælling, stikprøveudtræk, opslag på enkelte hits eller procentregning, `inspect` findes netop for at slå enkelte hits op uden at skrive en engangs-python-snippet. Din opgave er de kvalitative vurderinger, ikke regnestykkerne.

### 1. Find profilen

Kald `mcp__Overskrift_dk__list_search_terms`. Match brugerens navn mod `title`, også delvist. Ved flere kandidater: spørg hvilken, med AskUserQuestion. Notér `id` og `searchterm` ordret.

### 2. Afklar formålet

Formålet afgør hvad der er støj. Rækkefølge:

1. Læs memory: `mcp__memory__memory_list`, derefter relevante `/areas/overskrift-*.md`. Formålet kan være noteret fra en tidligere audit.
2. Kan formålet udledes 100 % entydigt af titlen (fx et unikt firmanavn), brug det og skriv i rapporten hvad du har lagt til grund.
3. Ellers: spørg med AskUserQuestion. Spørg om hvem eller hvad der overvåges, hvad omtalen bruges til, og hvad der udtrykkeligt IKKE er interessant.

Når brugeren har oplyst formålet, skriv det til memory i samme tur, så næste audit ikke skal spørge igen. Tilføj en linje til `/areas/overskrift-soegestrenge.md` i formen: `- [stated] Formål med søgeprofilen "<titel>" (id <id>): <formål>`. Læs filen først for at få version-token.

### 3. Hent rådata

Kald `mcp__Overskrift_dk__get_media_hits` med `term` = profilens id, `date_from` = 30 dage siden, `date_to` = i dag.

Er `_meta.counts.total` under 50, udvid perioden og hent igen: 90 dage, så 180, så 365. Stop ved 50 hits eller ved 365 dage. Er der stadig under 50 hits på et år, kør auditten alligevel og skriv tydeligt i rapporten at datagrundlaget er spinkelt.

En aktiv profil kan returnere flere millioner tegn på en måned. Det er ikke et problem, men det afgør hvordan svaret skal håndteres:

- Er svaret for stort til at læse ind, bliver det gemt som en fil, og filstien står i fejlbeskeden. Kopiér stien og brug filen direkte i næste trin. Læs aldrig rådata ind i sin helhed.
- Kommer svaret ind i samtalen, fordi profilen er lille, så skriv det til `raa.json` i arbejdsmappen, så resten af arbejdsgangen er den samme.
- Flere perioder kan hentes hver for sig og gives til scriptet samlet. Dubletter fjernes på url.

### 4. Skriv scriptet og kør lint

Tjek først om `overskrift_audit.py` allerede findes i arbejdsmappen fra en tidligere kørsel i denne session, fx med `test -f overskrift_audit.py && echo findes`. Findes den, brug den som den er. Kun hvis den mangler, skriv koden fra afsnittet **Script** ordret til `overskrift_audit.py`. At genskrive filen unødigt koster flere tusind tokens uden at ændre resultatet.

```bash
python3 overskrift_audit.py lint '<søgestrengen ordret>'
```

Scriptet finder disse fejl: ubalancerede anførselstegn, ubalancerede parenteser, `*`, `+` eller `-` brugt som operator inde i en frase, `*` der ikke står sidst i termen, og `+` eller `-` efterfulgt af mellemrum. Bemærk at en bindestreg midt i et ord, fx `"Laila Bøgh-Pedersen"`, er almindelig ortografi og ikke en fejl. Kun en `+` eller `-` i starten af et ord inde i frasen flagges.

Derudover giver scriptet advarsler: dubletter, termer der allerede dækkes af et wildcard, wildcard-stammer på tre tegn eller derunder, og overflødigt whitespace.

Advarslen `blandet_operator` er en særlig sag. Den udløses kun når et `+` står på topniveau samtidig med frie OR-termer, altså den situation hvor de frie termer ikke udvider resultatsættet. Den udløses IKKE af `(+x +y)`, hvor plusserne sidder inde i en gruppe, for det er normal opsætning. Får du advarslen, så mål det empirisk i trin 6 før du kalder det en fejl. Scriptets lint fanger derimod IKKE `+(A +(B C))`-fejlen beskrevet ovenfor, den ser syntaktisk gyldig ud. Den skal findes ved manuel læsning af parentesstrukturen plus empirisk test i trin 6, hver gang du enten reviderer en profil eller selv skriver en ny gren.

### 5. Byg det kompakte datasæt

```bash
python3 overskrift_audit.py prepare raa.json [raa2.json ...] --out hits.jsonl
```

Dette fjerner markeringstags men gemmer de markerede tekststumper i feltet `m`, fjerner dubletter på url, normaliserer kildenavne og skærer uddraget ned til 160 tegn som standard. Resultatet er én kompakt linje pr. hit, som resten af arbejdsgangen bygger på. Skriv aldrig `hits.jsonl` i hånden.

### 6. Se hvad udtrykkene faktisk rammer

```bash
python3 overskrift_audit.py expansions --term '<søgestrengen>' --raw raa.json [raa2.json ...]
```

Dette er det trin der typisk finder de reelle problemer. Scriptet folder grupper ud, tager hvert udtryk for sig og viser hvilke ordformer i resultatsættet der faktisk udløste et match. Hver overskrift fortæller også udtrykkets rolle: `or`, `obligatorisk`, `krav i gruppen ...`, `en af flere i gruppen ...` eller `stopord`. Læs rollen, før du fortolker tallene.

Standardvisningen viser 15 former pr. udtryk, plus alt der er markeret til gennemsyn. Er det ikke nok til at vurdere et wildcard med mange former, brug `--vis 30`. Gå ikke højere end nødvendigt, den lange hale af enkelt-hit-former ændrer sjældent konklusionen.

Læs de fire ting det svarer på:

- **Wildcards**: hvilke former stammen har ramt, hvor mange hits hver form står for, og hvor mange hits der udelukkende hviler på netop den form. Kolonnen "eneste form" er den vigtige: en form med mange eneste-hits bærer resultatsættet, en form med nul kan fjernes uden tab.
- **Termer uden wildcard**: former der ligger tæt på termen men ikke er dækket af den. Det er kandidater til dækningshuller, fx bøjninger og sammensætninger.
- **Stopord**: former der er sluppet igennem alligevel, typisk ejefald eller sammenskrivning. Står der LÆK, er stopordet ufuldstændigt, og det skal med i rapporten.
- **Til gennemsyn**: former der ligner tilfældige tegnfølger fra forkortede links, plus listen over de hits der udelukkende hviler på dem.

**Markeringen "til gennemsyn" er en indikation, ikke en dom.** Heuristikken bygger på cifre, skift mellem store og små bogstaver og vokalandel, og den tager fejl begge veje: den kan markere et legitimt socialt handle med mange konsonanter, og den fanger ikke alt. Brug `inspect` til at slå de markerede hits op og se konteksten, før noget kaldes støj i rapporten. Afvis frit scriptets markeringer, det er meningen.

Har strengen `+`-termer, så tjek dem mod deres rækkevidde, ikke mod hele resultatsættet:

- Et `+` på topniveau, altså rollen `obligatorisk`, skal matche stort set alle hits. Gør det ikke det, virker operatoren ikke som forventet, og det skal med i rapporten.
- Et `+` med rollen `krav i gruppen ...` skal IKKE matche alle hits. Grenen er sideordnet, og de øvrige udtryk henter deres egne hits. Mål i stedet hvad grenen bidrager med: findes der hits der kun kan komme derfra, og findes der hits fra de frie termer som ikke opfylder gruppens krav. Er svaret ja til det sidste, opfører søgningen sig som forventet.
- Vær særligt opmærksom hvis et udtryk der efter din læsning burde være et krav sammen med et andet (fx et brand-navn der skal optræde sammen med en produktkategori), i stedet rapporteres med rollen `en af flere i gruppen ...` eller `or`. Det er symptomet på `+(A +(B C))`-fejlen: A er blevet en fri OR-alternativ i stedet for et krav. Løsningen er at omskrive til `(+A +(B C))`, se afsnittet om operatorernes rækkevidde ovenfor.

### 7. Vurdér relevansen

```bash
python3 overskrift_audit.py sample --hits hits.jsonl --n 120 --out sample.jsonl
```

Udtrækket er stratificeret: proportionalt pr. kanal og spredt jævnt over perioden. Er der 120 hits eller færre, så brug hele `hits.jsonl` i stedet og spring stikprøven over.

120 er standarden og er nok til en stabil vurdering i langt de fleste tilfælde. Gå kun op til `--n 200` hvis den første gennemgang giver en støjprocent der ligger tæt på 20 % eller 50 %, grænserne der afgør anbefalingen i trin 8, og hvor et bredere datagrundlag reelt kan ændre konklusionen. Er støjprocenten tydeligt lav, tydeligt høj, eller er der under to hits i spil pr. udtryk, er 120 rigeligt.

Kommandoen udskriver én kompakt linje pr. hit, uden fast kolonnebredde: `id kanal|kilde|titel|uddrag`.

Gå listen igennem og afgør for hvert hit, om omtalen er relevant i forhold til formålet fra trin 2. Vær særligt opmærksom på de indeks, trin 6 markerede. Er uddraget for kort til at afgøre noget, brug `inspect` til at hente den fulde tekst i stedet for at gætte:

```bash
python3 overskrift_audit.py inspect --raw raa.json [raa2.json ...] --ids 27,44,89
```

Dette printer renset titel, kilde, dato, url og fuld tekst for de angivne id'er, id'erne er de samme som i `hits.jsonl`/`sample.jsonl`. Brug den i stedet for at skrive python til at læse `raa.json` selv, den er hurtigere at læse og fylder mindre.

```bash
python3 overskrift_audit.py mark --hits sample.jsonl --noise 12,44,88 --unsure 7,9
```

Alt der ikke nævnes bliver relevant. Støj betyder et hit der matcher teknisk, men ikke handler om det brugeren overvåger. Usikre tælles ikke med i støjprocenten, men rapporteres separat.

### 8. Kør støjanalysen

```bash
python3 overskrift_audit.py attribute --term '<søgestrengen>' --hits sample.jsonl [--population <total>]
```

Giv `--population` når du har brugt en stikprøve, så udskrives støjprocenten med usikkerhedsinterval. Er intervallet bredt nok til at det ændrer en anbefaling (fx krydser 20 % eller 50 % grænsen), gå tilbage til trin 7 og øg `--n`. Scriptet fordeler hits og støj pr. udtryk, viser hvilke kilder der bidrager mest støj, og lister hits der ikke kunne attribueres.

Bemærk at `attribute` behandler en hel parentesgruppe som ét samlet udtryk med OR-logik internt, uanset om gruppen reelt indeholder `+`-krav. Tallene for en sammensat gren (fx en hel Abus/iloq/salto-gren i én søgning) fortæller derfor kun noget om grenen som helhed, ikke om de enkelte mærker i den. Brug altid `expansions` fra trin 6 til at forstå fordelingen mellem de enkelte led i en sammensat gren, `attribute` alene er ikke nok til at diagnosticere `+(A +(B C))`-fejlen.

Læs anbefalingskolonnen som beslutningsstøtte, ikke som facit:

- **fjern** betyder at udtrykket kun leverer unikke hits der er støj. Verificér ved at kigge på dem, brug `inspect` på deres id'er
- **indsnævr** betyder høj støjandel, men også unikke relevante hits. Foreslå en frase, en nærhedssøgning eller et stopord i stedet for at slette
- **død** betyder nul hits i perioden. Kan være en stavefejl, et for snævert wildcard, eller bare et navn der ikke har været omtalt. Afgør ud fra termen selv, og lad tvivlen komme termen til gode. En sæson- eller begivenhedsterm kan være død uden for sæsonen og livlig i den, så tjek en periode hvor den burde være aktiv, før du foreslår at fjerne den. Er et udtryk et velkendt firmanavn der er blevet omdøbt eller sammenlagt (fx en fusion), tjek også om den nyere stavemåde (ofte sammenskrevet, fx "dormakaba" i stedet for "Dorma Kaba") er den der reelt bruges i pressen i dag

Har strengen kun ét eller to udtryk, siger tabellen ikke meget. Så er det trin 6 der bærer analysen, og støjen beskrives bedst grupperet i navngivne klasser med antal.

Stopord kan ikke måles på hentede data, for de har allerede filtreret hits fra. Vurdér dem logisk, og husk lækagen fra trin 6. Et bredt stopord kan desuden fjerne legitime omtaler, så foreslå at gøre brede stopord til fraser eller nærhedssøgninger.

Bemærk: attribution matcher mod titel, uddrag og markeringer, ikke mod hele artikelteksten, og et snævert uddrag (trin 5's 160 tegn) kan i sjældne tilfælde klippe en term midt i et ord og give et falsk match ved uddragets grænse. Virker et enkelt udtryks tal usandsynligt, fx en "død" frase du ved forekommer, dobbelttjek med `inspect` på et par af de relevante id'er før du konkluderer.

### 9. Find dækningshuller

Støj er kun den halve historie. Start med de udækkede former fra trin 6, de er målt i data. Gennemgå derefter systematisk:

- Ejefaldsformer af alle navne i anførselstegn, jf. brugerens konvention
- Stavevarianter, bindestreg mod mellemrum, med og uden accent, dansk mod engelsk navn
- Almindelige fejlstavninger af navnet
- Forkortelser og fulde navne, begge veje
- Domænenavne og URL-stumper, fx `"eksempelforening.dk"`
- Sociale handles og hashtags
- Centrale personer knyttet til organisationen, direktør, formand, talsperson
- Produktnavne, kampagnenavne, arrangementsnavne
- Entiteter der optræder gentagne gange i de relevante hits uden at stå i søgestrengen. Det er det stærkeste empiriske signal om et hul, og det kan tælles: opgiv hvor mange af hittene der nævner navnet

Foreslå kun termer du kan begrunde. Marker hvert forslag med forventet risiko for støj. Er et foreslået navn knyttet til en post der kan skifte, fx en formand på valg, så skriv det som en note til profilen.

### 10. Skriv rapporten

Struktur, i denne rækkefølge:

1. **Profil og datagrundlag**: titel, id, periode, antal hits, kanalfordeling, om der er vurderet alle eller en stikprøve, og stikprøvens størrelse
2. **Formål lagt til grund**: én til to sætninger, så brugeren kan korrigere
3. **Fejl i søgestrengen**: fejl først, så advarsler. Er der ingen, skriv det i én linje
4. **Støj pr. udtryk**: tabellerne fra trin 6 og 8, med din fortolkning under. Grupér gerne støjen i navngivne klasser med antal
5. **Støjkilder**: hvilke medier eller kanaler der står for støjen
6. **Dækningshuller**: forslag med begrundelse og støjrisiko
7. **Revideret søgestreng**: kun hvis der er fundet fejl eller målbar støj. Ellers en kort blåstempling. Læg den nye streng i en kodeblok, klar til indsættelse, og list ændringerne punkt for punkt med begrundelse. Før du afleverer en revideret streng, kør trin 6 (`expansions`) på DEN NYE streng, ikke kun den gamle, og bekræft at hvert tiltænkt obligatorisk led reelt opfører sig som et krav og ikke som en fri OR-alternativ, jf. faldgruben under "Operatorernes rækkevidde". At foreslå en streng uden denne kontrol er den hyppigste kilde til fejl i selve rapporten. Sig eksplicit at skill'en ikke kan gemme strengen i Overskrift, det skal brugeren selv gøre, og at det faktiske antal hits i Overskrifts egen optælling bør tjekkes før strengen gemmes, især hvis reviderede led stadig bruger brede kontekstord
8. **Forbehold**: datagrundlagets størrelse, stikprøveusikkerhed, hits der ikke kunne attribueres, stopord der ikke kan måles, støj der ikke kan fjernes med en søgestreng, og at `+` i Overskrift virker på hele dokumentet og derfor ikke garanterer nærhed mellem to krævede ord

Stilregler: dansk, konkret, ingen tankestreg. Brug komma, kolon eller linjeskift i stedet. Ingen ros uden dækning. Er profilen god, så sig det kort og lad være med at opfinde forbedringer. Overhold reglen om sprogbrug og teknologinavne i hele rapporten.

En særlig regel om påstande: når du siger, at et udtryk ikke virker som brugeren tror, skal påstanden være målt, ikke udledt af syntaksen. Skriv tallet der viser det. Kan du ikke måle det, så skriv det som et åbent spørgsmål med en test brugeren kan køre.

## Script

Skriv denne fil ordret til `overskrift_audit.py`, men kun hvis den ikke allerede findes i arbejdsmappen fra denne session, se trin 4.

```python
#!/usr/bin/env python3
"""Deterministisk lint og stoejanalyse af Overskrift-soegeprofiler."""
import argparse, html, json, math, re, sys
from collections import Counter, defaultdict

# ---------- parsing ----------

def scan(s):
    """Split en soegestreng i topniveau-udtryk."""
    exprs, i, n = [], 0, len(s)
    while i < n:
        if s[i].isspace():
            i += 1
            continue
        prefix = ''
        if s[i] in '+-':
            prefix = s[i]
            i += 1
            if i >= n or s[i].isspace():
                exprs.append({'raw': prefix, 'prefix': prefix, 'kind': 'dangling'})
                continue
        if s[i] == '(':
            depth, j = 0, i
            while j < n:
                c = s[j]
                if c == '"':
                    j += 1
                    while j < n and s[j] != '"':
                        j += 1
                elif c == '(':
                    depth += 1
                elif c == ')':
                    depth -= 1
                    if depth == 0:
                        j += 1
                        break
                j += 1
            raw = s[i:j]
            inner = raw[1:-1] if raw.endswith(')') else raw[1:]
            i = j
            exprs.append({'raw': prefix + raw, 'prefix': prefix, 'kind': 'group',
                          'terms': scan(inner)})
        elif s[i] == '"':
            j = i + 1
            while j < n and s[j] != '"':
                j += 1
            text = s[i + 1:j]
            i = min(j + 1, n)
            prox = None
            m = re.match(r'~(\d+)', s[i:])
            if m:
                prox = int(m.group(1))
                i += m.end()
            exprs.append({'raw': prefix + '"' + text + '"' + (('~%d' % prox) if prox else ''),
                          'prefix': prefix, 'kind': 'phrase', 'text': text, 'prox': prox})
        else:
            j = i
            while j < n and not s[j].isspace() and s[j] not in '()':
                j += 1
            exprs.append({'raw': prefix + s[i:j], 'prefix': prefix, 'kind': 'word', 'text': s[i:j]})
            i = j
    return exprs

# ---------- lint ----------

def _e(kode, besked):
    return {'niveau': 'FEJL', 'kode': kode, 'besked': besked}


def _w(kode, besked):
    return {'niveau': 'ADVARSEL', 'kode': kode, 'besked': besked}


def lint(s):
    out = []
    if s.count('"') % 2:
        out.append(_e('ubalancerede_anfoerselstegn',
                      'Ulige antal anfoerselstegn (%d). Frasen lukkes aldrig.' % s.count('"')))
    depth, i = 0, 0
    while i < len(s):
        c = s[i]
        if c == '"':
            i += 1
            while i < len(s) and s[i] != '"':
                i += 1
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth < 0:
                out.append(_e('ubalancerede_parenteser',
                              'Lukkeparentes uden matchende aabning ved position %d.' % i))
                depth = 0
        i += 1
    if depth > 0:
        out.append(_e('ubalancerede_parenteser', '%d aaben(ne) parentes(er) mangler lukning.' % depth))
    for m in re.finditer(r'"([^"]*)"', s):
        inner = m.group(1)
        if '*' in inner:
            out.append(_e('wildcard_i_frase',
                          'Wildcard inde i frasen "%s". * virker ikke i anfoerselstegn.' % inner))
        for om in re.finditer(r'(?:^|\s)([+-])\S', inner):
            out.append(_e('operator_i_frase',
                          'Operatoren "%s" virker ikke inde i frasen "%s".' % (om.group(1), inner)))
    outside = re.sub(r'"[^"]*"', lambda m: ' ' * len(m.group(0)), s)
    for tm in re.finditer(r'\S+', outside):
        core = tm.group(0).strip('()').lstrip('+-')
        if '*' in core:
            if core == '*':
                out.append(_e('tomt_wildcard', 'Et enkeltstaaende * er ikke en gyldig term.'))
            elif core.count('*') > 1 or not core.endswith('*'):
                out.append(_e('wildcard_placering',
                              'Wildcard skal staa sidst i termen. Fandt "%s".' % tm.group(0)))
    for m in re.finditer(r'(?:^|\s)([+-])(?:\s|$)', s):
        out.append(_e('operator_uden_term',
                      'Et "%s" efterfulgt af mellemrum har ingen effekt.' % m.group(1)))

    tops = scan(s)
    seen = set()
    for e in tops:
        k = e.get('raw', '').lower()
        if k in seen:
            out.append(_w('dublet', 'Termen %s optraeder flere gange.' % e['raw']))
        seen.add(k)
    plain = [e for e in tops if e['kind'] == 'word' and not e['prefix']]
    stems = [e['text'].rstrip('*').lower() for e in plain if e['text'].endswith('*')]
    for e in plain:
        t = e['text'].lower()
        if t.endswith('*'):
            continue
        for st in stems:
            if st and t.startswith(st):
                out.append(_w('overfloedig_term',
                              'Termen %s daekkes allerede af %s*.' % (e['text'], st)))
                break
    for st in set(stems):
        if len(st) <= 3:
            out.append(_w('kort_wildcard',
                          'Wildcard-stammen "%s*" er kort og kan give bred stoej.' % st))
    if s != s.strip():
        out.append(_w('whitespace', 'Soegestrengen har foranstillet eller efterfoelgende mellemrum.'))
    if any(e['prefix'] == '+' for e in tops) and any(e['prefix'] == '' for e in tops):
        out.append(_w('blandet_operator',
                      'Et + paa topniveau goer termen til krav for hele soegningen, saa de frie '
                      'OR-termer udvider ikke resultatsaettet. Maal det empirisk foer du kalder '
                      'det en fejl. Gaelder ikke plus inde i en gruppe.'))
    return out

# ---------- raadata ----------

TAGRX = re.compile(r'<[^>]+>')
MARKRX = re.compile(r'<mark>(.*?)</mark>', re.I | re.S)


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(TAGRX.sub('', s or ''))).strip()


def marks_of(*fields):
    out, seen = [], set()
    for f in fields:
        for m in MARKRX.findall(f or ''):
            t = clean(m)
            if t and t.lower() not in seen:
                seen.add(t.lower())
                out.append(t)
    return out


def load_posts(paths):
    """Laes et eller flere raa get_media_hits-svar. Dubletter fjernes paa url."""
    posts, seen, meta = [], set(), []
    for p in paths:
        with open(p, encoding='utf-8') as fh:
            data = json.load(fh)
        q = (data.get('_meta') or {}).get('query') or {}
        c = (data.get('_meta') or {}).get('counts') or {}
        meta.append({'fil': p, 'searchterm': q.get('searchterm'), 'total': c.get('total')})
        for post in data.get('posts', []):
            u = post.get('item_url') or ''
            if u and u in seen:
                continue
            seen.add(u)
            posts.append(post)
    return posts, meta


def post_text(p):
    return ' '.join(clean(p.get(k)) for k in ('item_title', 'item_desc', 'item_summary'))


def prepare(paths, out, snippet):
    posts, meta = load_posts(paths)
    rows = []
    for p in posts:
        g = p.get('groupkey') or ''
        src = 'LinkedIn' if g == 'linkedin' else clean(p.get('title'))
        rows.append({
            'i': len(rows) + 1,
            't': clean(p.get('item_title')),
            'm': marks_of(p.get('item_title'), p.get('item_summary'), p.get('item_desc')),
            's': src or g or 'ukendt',
            'g': g,
            'd': (p.get('pubdate') or '')[:10],
            'u': p.get('item_url') or '',
            'x': clean(p.get('item_desc'))[:snippet],
            'rel': None,
        })
    with open(out, 'w', encoding='utf-8') as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    return {'kilder': meta, 'unikke_hits': len(rows), 'ud': out}

# ---------- ekspansioner ----------

TAIL = r'[\w\-]'
VOWELS = set('aeiouyæøåàáâãäèéêëìíîïòóôõöùúûü')


def id_candidate(tok, stem):
    """Ser formen ud som en tilfaeldig tegnfoelge fra et forkortet link.
    Kun en indikation, aldrig en dom. Bekraeft altid manuelt paa konteksten
    foer en form kaldes stoej i rapporten."""
    tail = tok[len(stem):]
    if len(tail) < 4:
        return False
    if is_slug(tok):
        return False
    letters = [c for c in tail if c.isalpha()]
    if any(c.isdigit() for c in tail) and letters:
        return True
    switches = sum(1 for a, b in zip(letters, letters[1:]) if a.isupper() != b.isupper())
    if switches >= 2:
        return True
    v = sum(c.lower() in VOWELS for c in tail)
    return len(tail) >= 5 and v / len(tail) < 0.15


def is_slug(tok):
    """Lang form med flere bindestreger eller understreger: typisk en url-stump."""
    return len(tok) >= 15 and (tok.count('-') + tok.count('_')) >= 2


def _flatten(exprs, prefix='', grp=None):
    """Fold grupper ud til enkeltudtryk. Husk baade operatoren og hvilken gruppe
    udtrykket sad i, for et + inde i en gruppe er kun et krav inden for den
    gruppe, ikke for hele soegningen."""
    out = []
    for e in exprs:
        pre = e.get('prefix') or prefix
        if e['kind'] == 'group':
            out.extend(_flatten(e.get('terms', []), pre,
                                grp or {'raw': e.get('raw'), 'prefix': e.get('prefix') or ''}))
        elif e['kind'] in ('word', 'phrase'):
            out.append((pre, e, grp))
    return out


def probe_regex(e):
    """Regex der ogsaa fanger laengere former end udtrykket selv,
    saa boejninger og sammenskrivninger bliver synlige."""
    if e['kind'] == 'word':
        stem = e['text'].rstrip('*')
        return re.compile(r'\b' + re.escape(stem) + TAIL + '*', re.I | re.U), stem
    ws = [w for w in re.split(r'\W+', e.get('text', '')) if w]
    if not ws:
        return None, ''
    pat = r'\b' + r'\W+'.join(re.escape(w) for w in ws) + TAIL + '*'
    return re.compile(pat, re.I | re.U), ' '.join(ws)


def expansions(term, posts):
    tops = [x for x in scan(term) if x['kind'] != 'dangling']
    flat = _flatten(tops)
    texts = []
    for p in posts:
        texts.append((post_text(p) + ' ' + (p.get('item_url') or ''), p))
    res = []
    cand_posts, pos_posts = {}, {}
    for pre, e, grp in flat:
        rx, stem = probe_regex(e)
        if rx is None:
            continue
        wild = e['kind'] == 'word' and e['text'].endswith('*')
        forms, only, cands = {}, Counter(), set()
        hit_posts = set()
        for n, (txt, p) in enumerate(texts):
            found = {}
            for m in rx.finditer(txt):
                found.setdefault(m.group(0).lower(), m.group(0))
            if not found:
                continue
            hit_posts.add(n)
            for low, orig in found.items():
                d = forms.setdefault(low, {'vis': orig, 'posts': set()})
                d['posts'].add(n)
            if len(found) == 1:
                only[list(found)[0]] += 1
        rows = []
        for low, d in sorted(forms.items(), key=lambda kv: -len(kv[1]['posts'])):
            exact = low == stem.lower() or low.replace(' ', '') == stem.lower().replace(' ', '')
            daekket = wild or exact
            slug = is_slug(low)
            cand = wild and not exact and not slug and id_candidate(low, stem.lower())
            if cand:
                cands |= d['posts']
            rows.append({'form': d['vis'], 'posts': len(d['posts']), 'eneste': only.get(low, 0),
                         'daekket': daekket, 'kandidat': cand, 'slug': slug})
        if pre != '-':
            for n in hit_posts:
                pos_posts.setdefault(n, set())
            for low, d in forms.items():
                for n in d['posts']:
                    pos_posts.setdefault(n, set()).add((e['raw'], low))
            for n in cands:
                cand_posts.setdefault(n, set())
        res.append({'udtryk': ('-' if pre == '-' else '') + e['raw'].lstrip('+-'),
                    'operator': pre or 'or', 'egen': e.get('prefix') or '',
                    'gruppe': grp, 'wildcard': wild,
                    'kind': e['kind'], 'posts': len(hit_posts), 'former': rows})
    # posts der udelukkende hviler paa gennemsynskandidater
    kun_kandidat = []
    for n, pairs in pos_posts.items():
        if not pairs:
            continue
        ok = False
        for raw, low in pairs:
            for r in res:
                if r['udtryk'].lstrip('-') == raw.lstrip('+-'):
                    for f in r['former']:
                        if f['form'].lower() == low and not f['kandidat']:
                            ok = True
        if not ok:
            kun_kandidat.append(n)
    return res, sorted(kun_kandidat)


def rolle(r):
    """Hvad udtrykket betyder i soegningen. Et + inde i en gruppe uden egen
    operator er kun et krav inden for gruppen, som selv er en sideordnet gren."""
    if r['operator'] == '-':
        return 'stopord'
    egen, grp = r.get('egen') or '', r.get('gruppe')
    if not grp:
        return 'obligatorisk' if egen == '+' else 'or'
    navn = grp.get('raw')
    if egen == '+':
        return 'krav i gruppen %s' % navn
    return ('en af flere i den obligatoriske gruppe %s' % navn
            if grp.get('prefix') == '+' else 'en af flere i gruppen %s' % navn)


def md_expansions(res, kun_kandidat, posts, vis=15):
    L = []
    for r in res:
        art = rolle(r)
        L.append('### `%s`  (%s%s, %d hits)' % (r['udtryk'], art,
                                                ', wildcard' if r['wildcard'] else '', r['posts']))
        if r['operator'] == '-':
            laek = [f for f in r['former'] if f['posts']]
            if laek:
                L.append('LAEK: stopordet fanger ikke disse former, som staar i resultatsaettet:')
                for f in laek:
                    L.append('  %-34s %d hits' % (f['form'], f['posts']))
            else:
                L.append('Ingen boejede eller sammenskrevne former sluppet igennem.')
            L.append('')
            continue
        daekket = [f for f in r['former'] if f['daekket']]
        udaekket = [f for f in r['former'] if not f['daekket']]
        top = daekket[:vis] + [f for f in daekket[vis:] if f['kandidat']]
        L.append('| Form | Hits | Eneste form | Status |')
        L.append('|---|---:|---:|---|')
        for f in top:
            st = 'til gennemsyn' if f['kandidat'] else ('url-stump' if f['slug'] else '')
            L.append('| %s | %d | %d | %s |' % (f['form'], f['posts'], f['eneste'], st))
        rest = len(daekket) - len(top)
        if rest > 0:
            L.append('| ... %d flere former, ingen markeret | | | |' % rest)
        if udaekket:
            flere = [f for f in udaekket if f['posts'] >= 2][:10]
            L.append('')
            L.append('Former der IKKE er daekket af udtrykket, %d i alt, mulige daekningshuller:'
                     % len(udaekket))
            for f in flere:
                L.append('  %-34s %d hits' % (f['form'], f['posts']))
            if not flere:
                L.append('  alle med 1 hit, se --json for hele listen')
        L.append('')
    if kun_kandidat:
        L.append('### Hits der udelukkende hviler paa former markeret til gennemsyn: %d'
                 % len(kun_kandidat))
        L.append('Markeringen er en indikation, ikke en dom. Brug inspect paa dem foer du kalder dem stoej.')
        L.append('')
        L.append('| Dato | Kanal | Kilde | URL |')
        L.append('|---|---|---|---|')
        for n in kun_kandidat[:40]:
            p = posts[n]
            L.append('| %s | %s | %s | %s |' % ((p.get('pubdate') or '')[:10], p.get('groupkey'),
                                                clean(p.get('title'))[:34],
                                                (p.get('item_url') or '')[:70]))
    return '\n'.join(L)


# ---------- stikproeve, relevansmarkering og opslag ----------

def read_jsonl(path):
    rows = []
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(rows, path):
    with open(path, 'w', encoding='utf-8') as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')


def sample(rows, n):
    """Stratificeret udtraek: proportionalt pr. kanal, spredt jaevnt over perioden."""
    by = defaultdict(list)
    for r in rows:
        by[r.get('g') or 'ukendt'].append(r)
    tot, out = len(rows), []
    for g, rs in by.items():
        k = max(1, round(n * len(rs) / tot)) if tot else 0
        rs = sorted(rs, key=lambda r: r.get('d') or '')
        step = max(1, len(rs) // k) if k else 1
        out += [rs[i] for i in range(0, len(rs), step)][:k]
    return sorted(out, key=lambda r: r.get('i') or 0)


def sample_lines(rows, snippet_width=70):
    """Kompakt visning uden fast kolonnebredde, for at holde tokenforbruget nede
    naar der er mange raekker."""
    L = []
    for r in rows:
        kanal = (r.get('g') or '?')[:3]
        kilde = (r.get('s') or '')[:16]
        titel = (r.get('t') or '(uden titel)')[:40]
        snip = (r.get('x') or '')[:snippet_width]
        L.append('%d %s|%s|%s|%s' % (r.get('i') or 0, kanal, kilde, titel, snip))
    return '\n'.join(L)


def parse_ids(s):
    return {int(x) for x in re.split(r'[,\s]+', s or '') if x.strip().isdigit()}


def inspect(posts, ids):
    """Print renset fuldtekst for udvalgte hit-id'er, id = 1-baseret raekkefoelge
    som i prepare/sample. Erstatter ad hoc-kode til at slaa enkelte hits op."""
    L = []
    for i in sorted(ids):
        if i < 1 or i > len(posts):
            L.append('=== %d: findes ikke (kun %d hits)' % (i, len(posts)))
            continue
        p = posts[i - 1]
        L.append('=== %d | %s | %s' % (i, (p.get('pubdate') or '')[:10], clean(p.get('title'))))
        L.append('URL: %s' % (p.get('item_url') or ''))
        L.append('Titel: %s' % clean(p.get('item_title')))
        txt = clean(p.get('item_desc')) or clean(p.get('item_summary'))
        L.append('Tekst: %s' % txt)
        L.append('')
    return '\n'.join(L)


# ---------- matchning ----------

def _word_rx(w):
    w = w.strip()
    if w.endswith('*'):
        return r'\b' + re.escape(w[:-1]) + r'\w*'
    return r'\b' + re.escape(w) + r'\b'


def expr_regex(e):
    if e['kind'] == 'word':
        return _word_rx(e['text']) if e.get('text') else None
    if e['kind'] == 'phrase':
        ws = [w for w in re.split(r'\W+', e.get('text', '')) if w]
        if not ws:
            return None
        if e.get('prox'):
            gap = r'(?:\W+\w+){0,%d}\W+' % e['prox']
            fwd = gap.join(r'\b' + re.escape(w) + r'\b' for w in ws)
            rev = gap.join(r'\b' + re.escape(w) + r'\b' for w in reversed(ws))
            return '(?:%s|%s)' % (fwd, rev)
        return r'\b' + r'\W+'.join(re.escape(w) for w in ws) + r'\b'
    if e['kind'] == 'group':
        subs = [x for x in (expr_regex(t) for t in e.get('terms', [])) if x]
        return '(?:%s)' % '|'.join(subs) if subs else None
    return None


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    hw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - hw), min(1.0, c + hw))


def pct(a, b):
    return 0.0 if not b else 100.0 * a / b


def attribute(term, hits, population=None):
    tops = [e for e in scan(term) if e['kind'] != 'dangling']
    pos = [e for e in tops if e['prefix'] != '-']
    neg = [e for e in tops if e['prefix'] == '-']
    pats = []
    for e in pos:
        rx = expr_regex(e)
        pats.append((e['raw'], e['prefix'], re.compile(rx, re.I | re.U) if rx else None))
    per = {lab: {'hits': 0, 'unik': 0, 'stoej': 0, 'relevant': 0, 'usikker': 0,
                 'unik_relevant': 0, 'unik_stoej': 0, 'prefix': pre, 'kilder': Counter()}
           for lab, pre, _ in pats}
    src = defaultdict(lambda: {'hits': 0, 'stoej': 0})
    unattributed, judged, rel, noise, unsure = [], 0, 0, 0, 0
    for h in hits:
        text = ' '.join(str(h.get(k) or '') for k in ('t', 'x'))
        text += ' ' + ' '.join(h.get('m') or [])
        r = h.get('rel')
        if r is None:
            unsure += 1
        else:
            judged += 1
            rel += 1 if r else 0
            noise += 0 if r else 1
        s_ = h.get('s') or h.get('g') or 'ukendt'
        src[s_]['hits'] += 1
        if r == 0:
            src[s_]['stoej'] += 1
        matched = [lab for lab, _pre, rx in pats if rx and rx.search(text)]
        if not matched:
            unattributed.append(h.get('i'))
            continue
        for lab in matched:
            d = per[lab]
            d['hits'] += 1
            if r == 1:
                d['relevant'] += 1
            elif r == 0:
                d['stoej'] += 1
                d['kilder'][s_] += 1
            else:
                d['usikker'] += 1
        if len(matched) == 1:
            d = per[matched[0]]
            d['unik'] += 1
            if r == 1:
                d['unik_relevant'] += 1
            elif r == 0:
                d['unik_stoej'] += 1
    for lab, d in per.items():
        d['stoej_pct'] = pct(d['stoej'], d['stoej'] + d['relevant'])
        if d['hits'] == 0:
            d['anbefaling'] = 'doed'
        elif d['unik'] >= 3 and d['unik_relevant'] == 0 and d['unik_stoej'] > 0:
            d['anbefaling'] = 'fjern'
        elif d['stoej_pct'] >= 50:
            d['anbefaling'] = 'indsnaevr'
        elif d['stoej_pct'] >= 20:
            d['anbefaling'] = 'se efter'
        else:
            d['anbefaling'] = 'ok'
    lo, hi = wilson(noise, judged)
    n = len(hits)
    res = {
        'soegestreng': term,
        'antal_hits_vurderet': n,
        'population': population or n,
        'stikproeve': bool(population and population > n),
        'vurderet': judged, 'relevant': rel, 'stoej': noise, 'usikker': unsure,
        'stoej_pct': pct(noise, judged),
        'stoej_ci95': [round(lo * 100, 1), round(hi * 100, 1)],
        'ikke_attribueret': unattributed,
        'obligatoriske': [{'udtryk': lab, 'daekning_pct': round(pct(per[lab]['hits'], n), 1)}
                          for lab, pre, _ in pats if pre == '+'],
        'stopord': [e['raw'] for e in neg],
        'pr_udtryk': per,
        'kilder': dict(src),
    }
    return res


def md(res):
    L = []
    L.append('**Datagrundlag**: %d hits vurderet%s. Relevante %d, stoej %d, usikre %d.'
             % (res['antal_hits_vurderet'],
                (' som stikproeve af %d' % res['population']) if res['stikproeve'] else '',
                res['relevant'], res['stoej'], res['usikker']))
    if res['vurderet']:
        s = 'Samlet stoejandel: %.1f %%' % res['stoej_pct']
        if res['stikproeve']:
            s += ' (95 %% interval %.1f til %.1f)' % tuple(res['stoej_ci95'])
        L.append(s)
    L.append('')
    L.append('| Udtryk | Hits | Unikke | Stoej | Stoej % | Anbefaling |')
    L.append('|---|---:|---:|---:|---:|---|')
    for lab, d in sorted(res['pr_udtryk'].items(), key=lambda kv: -kv[1]['stoej']):
        L.append('| `%s` | %d | %d | %d | %.0f | %s |'
                 % (lab, d['hits'], d['unik'], d['stoej'], d['stoej_pct'], d['anbefaling']))
    noisy = sorted(((k, v) for k, v in res['kilder'].items() if v['stoej']),
                   key=lambda kv: -kv[1]['stoej'])[:10]
    if noisy:
        L.append('')
        L.append('| Kilde | Hits | Stoej |')
        L.append('|---|---:|---:|')
        for k, v in noisy:
            L.append('| %s | %d | %d |' % (k, v['hits'], v['stoej']))
    if res['obligatoriske']:
        L.append('')
        for o in res['obligatoriske']:
            L.append('Obligatorisk udtryk paa topniveau `%s` matcher %.1f %% af hits '
                     '(forventet naer 100).' % (o['udtryk'], o['daekning_pct']))
    if res['ikke_attribueret']:
        L.append('')
        L.append('Ikke attribueret til noget udtryk: %d hits, indeks %s'
                 % (len(res['ikke_attribueret']),
                    ', '.join(str(x) for x in res['ikke_attribueret'][:25])))
    if res['stopord']:
        L.append('')
        L.append('Stopord i strengen (kan ikke maales paa hentede data, vurder logisk): %s'
                 % ', '.join('`%s`' % x for x in res['stopord']))
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p1 = sub.add_parser('lint')
    p1.add_argument('term')
    p1.add_argument('--json', action='store_true')
    p2 = sub.add_parser('attribute')
    p2.add_argument('--term', required=True)
    p2.add_argument('--hits', required=True)
    p2.add_argument('--population', type=int, default=None)
    p2.add_argument('--json', action='store_true')
    p3 = sub.add_parser('prepare')
    p3.add_argument('files', nargs='+')
    p3.add_argument('--out', default='hits.jsonl')
    p3.add_argument('--snippet', type=int, default=160)
    p4 = sub.add_parser('expansions')
    p4.add_argument('--term', required=True)
    p4.add_argument('--raw', nargs='+', required=True)
    p4.add_argument('--vis', type=int, default=15)
    p4.add_argument('--json', action='store_true')
    p5 = sub.add_parser('sample')
    p5.add_argument('--hits', required=True)
    p5.add_argument('--n', type=int, default=120)
    p5.add_argument('--out', default='sample.jsonl')
    p6 = sub.add_parser('mark')
    p6.add_argument('--hits', required=True)
    p6.add_argument('--noise', default='')
    p6.add_argument('--unsure', default='')
    p6.add_argument('--rest', type=int, default=1)
    p7 = sub.add_parser('inspect')
    p7.add_argument('--raw', nargs='+', required=True)
    p7.add_argument('--ids', required=True)
    a = ap.parse_args()

    if a.cmd == 'inspect':
        posts, _meta = load_posts(a.raw)
        print(inspect(posts, parse_ids(a.ids)))
        return

    if a.cmd == 'sample':
        rows = read_jsonl(a.hits)
        sub_rows = sample(rows, a.n)
        write_jsonl(sub_rows, a.out)
        print('Stikproeve: %d af %d hits, skrevet til %s' % (len(sub_rows), len(rows), a.out))
        print(sample_lines(sub_rows))
        return

    if a.cmd == 'mark':
        rows = read_jsonl(a.hits)
        noise, unsure = parse_ids(a.noise), parse_ids(a.unsure)
        for r in rows:
            i = r.get('i')
            r['rel'] = None if i in unsure else (0 if i in noise else a.rest)
        write_jsonl(rows, a.hits)
        print(json.dumps({'fil': a.hits, 'hits': len(rows), 'stoej': len(noise),
                          'usikre': len(unsure),
                          'relevante': len(rows) - len(noise) - len(unsure)}, ensure_ascii=False))
        return

    if a.cmd == 'prepare':
        print(json.dumps(prepare(a.files, a.out, a.snippet), ensure_ascii=False, indent=1))
        return

    if a.cmd == 'expansions':
        posts, meta = load_posts(a.raw)
        res, kun = expansions(a.term, posts)
        if a.json:
            print(json.dumps({'meta': meta, 'udtryk': res, 'kun_kandidat': kun},
                             ensure_ascii=False, indent=1))
            return
        print('Hits i alt: %d' % len(posts))
        print(md_expansions(res, kun, posts, vis=a.vis))
        return

    if a.cmd == 'lint':
        findings = lint(a.term)
        parsed = [{'raw': e['raw'], 'kind': e['kind'], 'prefix': e['prefix']} for e in scan(a.term)]
        if a.json:
            print(json.dumps({'udtryk': parsed, 'fund': findings}, ensure_ascii=False, indent=1))
            return
        print('Udtryk (%d):' % len(parsed))
        for e in parsed:
            print('  %-40s %s%s' % (e['raw'], e['kind'],
                                    ' [%s]' % e['prefix'] if e['prefix'] else ''))
        if not findings:
            print('\nIngen fejl eller advarsler.')
            return
        print('')
        for f in findings:
            print('%-9s %-26s %s' % (f['niveau'], f['kode'], f['besked']))
        return

    hits = []
    with open(a.hits, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line:
                hits.append(json.loads(line))
    res = attribute(a.term, hits, a.population)
    print(json.dumps(res, ensure_ascii=False, indent=1) if a.json else md(res))


if __name__ == '__main__':
    main()
```

## Kendte begrænsninger, skriv dem i rapporten når de gælder

- Markeringen "til gennemsyn" i trin 6 er en indikation, ikke en dom. Den bygger på cifre, skift mellem store og små bogstaver og vokalandel, og den tager fejl begge veje. Bekræft hvert markeret hit manuelt med `inspect`, og afvis frit scriptets forslag
- Attribution er en approksimation. Den matcher udtrykkene mod titel, uddrag og de markerede tekststumper, ikke mod hele artikelteksten. Et hit kan derfor lande i "ikke attribueret", selvom matchet lå længere nede i teksten. Uddraget er som standard kun 160 tegn, kortere end i den fulde rådata, så brug `inspect` hvis et enkelt udtryks tal virker usandsynligt
- En mindre stikprøve (standard 120) giver et bredere usikkerhedsinterval end en større. Det er en bevidst afvejning: udvid kun til 200 hvis intervallet reelt kan ændre en anbefaling, se trin 7 og 8
- Podcasts og enkelte blogs kan matche på indhold der ikke følger med i eksporten, fx en transskription. De kan hverken be- eller afkræftes, og skal tælles som usikre
- Ved attribution behandles en gruppe som ét udtryk, hvor indholdet læses som OR. Kræver gruppen flere ting samtidig, fx `(+x +y)`, er attributionens tal for højt for den gren. Ekspansionsanalysen folder gruppen ud og navngiver rollen korrekt, så brug den til at fortolke grupper
- Stopord kan ikke evalueres på hentede data. Ekspansionsanalysen kan dog vise om noget er sluppet igennem i en bøjet form. Lækagetjekket er kun gyldigt, når rådata stammer fra netop den profil
- Støj fra tilfældige tegnfølger i forkortede links kan ikke fjernes med en søgestreng. Sig det åbent i stedet for at foreslå noget der ikke virker
- `+` i Overskrift virker på hele dokumentet, ikke på sætnings- eller afsnitsnærhed. Et krav som `+A +(B C)` udelukker ikke, at A og B/C optræder usammenhængende langt fra hinanden i en lang tekst. Det er en reel begrænsning ved boolske AND-krav i dette system, ikke en fejl i søgestrengen, og bør nævnes når en revideret streng stadig bruger brede kontekstord
- Et `+` skal stå direkte foran hvert enkelt obligatorisk led. `+(A +(B C))` er IKKE det samme som `(+A +(B C))`, det første gør A til en fri OR-alternativ ved siden af kravet B/C, ikke et krav sammen med det. Denne fejl giver ingen lint-advarsel og skal fanges ved manuel parentesanalyse plus empirisk test i trin 6, både i eksisterende profiler og i enhver ny streng du selv foreslår
- Bredt anvendte, polyseme danske ord (nøgle*, kæde*, adgang*, sikkerh*, salto* og lignende) rammer almindeligt sprogbrug uden forbindelse til den overvågede virksomhed. De bør kun bruges i søgestrenge når de er sammensat til noget mere specifikt (nøgleboks*, kædelås*, adgangskontrol*, sikringsanlæg*), og selv da er de ikke risikofrie, se punktet ovenfor om at + ikke giver nærhed
- Skill'en kan læse søgeprofiler, ikke skrive dem. Reviderede strenge skal indsættes manuelt i Overskrift, og det faktiske antal hits bør altid bekræftes i Overskrifts egen optælling før strengen gemmes, uanset hvor grundig analysen i denne skill har været