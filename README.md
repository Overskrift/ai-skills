# Overskrift's ai-skills

Åbne, genanvendelige AI-skills med instruktioner, scripts og visuelle assets til Claude, Codex, CoPilot og andre kompatible AI-agenter.

En *skill* er en mappe med en `SKILL.md`, som lærer en AI-agent at løse en bestemt opgave på en ensartet måde. Skillene her er lavet af [Overskrift.dk](https://overskrift.dk) til arbejdet med medieovervågning og medieomtaler.

## Skills

| Skill | Hvad den gør | Brug den når | Krav |
|-------|--------------|--------------|------|
| [`medieomtale-analyse`](skills/medieomtale-analyse/SKILL.md) | Laver en visuel medieanalyse som selvstændig HTML-fil og PowerPoint ud fra en JSON-eksport fra Overskrift.dk | Du har forbundet din AI til Overskrift via MCP, eller har hentet en JSON-fil med medieomtaler og vil have en rapport | Python 3, Node.js og `pptxgenjs` (`npm install` i skill-mappen) |
| [`overskrift-soegeprofil-audit`](skills/overskrift-soegeprofil-audit/SKILL.md) | Gennemgår en søgeprofil i Overskrift.dk: er søgestrengen korrekt, rammer den rigtigt, og mangler den noget. Resultatet er en rapport i chatten | Du vil vide, om en søgning larmer, går glip af omtaler eller kan forbedres | Python 3 |

Detaljer om arbejdsgang og format står i hver skills `SKILL.md`.

## Installation

Kopiér den eller de skill-mapper, du vil bruge, til din agents skills-mappe.

**Claude Code**

```bash
# til alle dine projekter
cp -r skills/medieomtale-analyse ~/.claude/skills/
# eller kun til ét projekt
cp -r skills/medieomtale-analyse <projekt>/.claude/skills/
```

**Claude.ai**: pak skill-mappen som zip-fil, og upload den under Indstillinger → Skills.

**Codex, CoPilot og andre agenter**: læg skill-mappen i den mappe, din agent henter skills fra. Se agentens egen dokumentation.

`medieomtale-analyse` skal have installeret sin npm-afhængighed én gang:

```bash
cd medieomtale-analyse && npm install
```

## Eksempler

- *"Giv mig en analyse af medieomtalerne der nævner folkeskolen for den seneste uge"* (forbinder via MCP) → `medieomtale-analyse`
- *"Analysér denne fil fra Overskrift og lav en rapport"* (vedhæft JSON-eksporten) → `medieomtale-analyse`
- *"Lav et eftersyn af søgeprofilen ‘Musik i Lejet’"* → `overskrift-soegeprofil-audit`

## Struktur

```
skills/
  <skill-navn>/
    SKILL.md      instruktioner og frontmatter (name, description)
    scripts/      kørbar kode (valgfri)
    assets/       logoer og andre filer (valgfri)
```

## Licens

MIT, se [LICENSE](LICENSE). Skills må frit anvendes, tilpasses og deles, også kommercielt. Kreditering af Overskrift.dk er værdsat, men ikke påkrævet.
