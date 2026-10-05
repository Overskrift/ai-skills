# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Overskrift.dk's open, reusable AI skills (Claude, Codex, Copilot and other compatible agents), MIT-style open usage per `README.md`. Each skill is a directory under `skills/<name>/` whose entry point is a `SKILL.md` (YAML frontmatter with `name` + `description`, then instructions). There is no repo-level build, lint or test setup; `install/` is currently empty. All skill content, user-facing output and skill prose are in **Danish** — keep new text in Danish.

The `description` in each SKILL.md frontmatter is the trigger text agents use to decide when to load the skill, so edit it deliberately.

## Skills

### `skills/medieomtale-analyse` — media-mention report from an Overskrift.dk JSON export

Design principle: everything deterministic lives in tested scripts; the agent only does the one qualitative step. Fix bugs/new needs in the scripts rather than re-implementing ad hoc in an analysis (SKILL.md says this explicitly).

Pipeline (run from the skill directory):

```bash
python3 scripts/compute_metrics.py <input.json> --outdir <dir> --org-name "<Navn>"   # → metrics.json + substantive.json (stdlib only)
# agent reads substantive.json, writes topics.json (exactly 5 topics, format in SKILL.md)
python3 scripts/render_html.py metrics.json substantive.json topics.json --logo assets/overskrift-logo.svg --out <navn>-medieanalyse-<måned><år>.html
npm install pptxgenjs   # once per environment; only dependency (package.json)
node scripts/render_pptx.js metrics.json topics.json --logo assets/overskrift-logo.png --out <navn>-medieanalyse-<måned><år>.pptx
```

Architecture notes that span files:
- `compute_metrics.py` dedupes posts on `item_url` first, and formats all dates in Danish (`DD/MM-YYYY`) and channel names in Danish; renderers must not re-format.
- `substantive.json` `idx` values are what `topics.json` `example_idx` refers to.
- `render_html.py` uses `svg_helpers.py` (hand-built SVG charts, `PALETTE`, `apportion_squares()`); `render_pptx.js` reimplements the same logic in JS (`apportionSquares()`). The Top 5 "waffle" chart is a fixed 10×10 grid allocated with largest-remainder apportionment against `metrics.total` (not the top-5 sum), with a grey "Øvrige omtaler" bucket — changes to allocation, palette or section order must be made in **both** the HTML and PPTX renderers to keep them consistent.
- PPTX has 7 fixed slides and no closing slide (logo sits bottom-right on the last one). Logo is prerendered PNG so no cairosvg is needed.

### `skills/overskrift-soegeprofil-audit` — audit of an Overskrift search profile

Single 976-line `SKILL.md`, no `scripts/` directory: the helper `overskrift_audit.py` is embedded verbatim in the "Script" section of SKILL.md, and the agent writes it out to the working directory at run time (only if not already present). Consequences when editing:
- The Python source lives inside the markdown; keep it in sync with the workflow steps that reference its subcommands (`lint`, `prepare`, `expansions`, `sample`, `mark`, `inspect`, `attribute`).
- The skill is used by Overskrift's customers, so the "Sprogbrug over for kunder" rules apply: never name underlying search/database technology or expose internal ids in the report; describe search behaviour functionally.
- Output is a report in chat, no files unless asked.
