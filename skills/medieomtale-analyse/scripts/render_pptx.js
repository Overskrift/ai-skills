#!/usr/bin/env node
/**
 * render_pptx.js — Renderer PowerPoint-præsentationen fra metrics.json og
 * topics.json. Al slide-layout, farvepalet og chart-opsætning er fast kode
 * her — det eneste input der varierer fra analyse til analyse er selve
 * data-filerne.
 *
 * Brug:
 *   node render_pptx.js <metrics.json> <topics.json> --logo <logo.png> --out <output.pptx>
 */
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

function parseArgs(argv) {
  const positional = [];
  const opts = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--logo") opts.logo = argv[++i];
    else if (argv[i] === "--out") opts.out = argv[++i];
    else positional.push(argv[i]);
  }
  return { metricsPath: positional[0], topicsPath: positional[1], ...opts };
}

const { metricsPath, topicsPath, logo, out } = parseArgs(process.argv.slice(2));
if (!metricsPath || !topicsPath || !out) {
  console.error("Brug: node render_pptx.js <metrics.json> <topics.json> --logo <logo.png> --out <output.pptx>");
  process.exit(1);
}

const metrics = JSON.parse(fs.readFileSync(metricsPath, "utf8"));
const topicsData = JSON.parse(fs.readFileSync(topicsPath, "utf8"));

const ORANGE = "FF7500", BLUE = "0055FF", BLACK = "000000", BGLIGHT = "F1F6FF", WHITE = "FFFFFF", MUTED = "5D6780", GREY = "E9E9E9", REST_GREY = "D7D9DD";
const PALETTE = ["FF7500", "0055FF", "16a34a", "7c3aed", "0d9488", "db2777", "ca8a04", "4338ca", "65a30d", "0891b2"];

// Samme "largest remainder"-metode som apportion_squares() i svg_helpers.py —
// se dén fil for hvorfor: garanterer at et waffle-gitter altid summer til
// nøjagtig 100 felter (fast 10x10), uanset afrundingsfejl i de enkelte andele.
function apportionSquares(values, nSquares = 100) {
  const total = values.reduce((a, b) => a + b, 0);
  if (total <= 0) return values.map(() => 0);
  const raw = values.map((v) => (v / total) * nSquares);
  const floors = raw.map((x) => Math.floor(x));
  let remainder = nSquares - floors.reduce((a, b) => a + b, 0);
  const order = raw
    .map((x, i) => [x - floors[i], i])
    .sort((a, b) => b[0] - a[0])
    .map(([, i]) => i);
  for (let k = 0; k < remainder; k++) floors[order[k]] += 1;
  values.forEach((v, i) => {
    if (v > 0 && floors[i] === 0) {
      let donor = 0;
      floors.forEach((f, j) => { if (f > floors[donor]) donor = j; });
      if (donor !== i && floors[donor] > 1) {
        floors[donor] -= 1;
        floors[i] += 1;
      }
    }
  });
  return floors;
}

const makeShadow = () => ({ type: "outer", color: "000000", blur: 8, offset: 2, angle: 135, opacity: 0.08 });

const pres = new pptxgen();
pres.defineLayout({ name: "WIDE", width: 13.333, height: 7.5 });
pres.layout = "WIDE";
const FONT = "Arial";

function bgSlide() {
  const s = pres.addSlide();
  s.background = { color: BGLIGHT };
  return s;
}

// ---------- Slide 1: Title ----------
{
  const s = pres.addSlide();
  s.background = { color: BLACK };
  s.addShape("rect", { x: 0, y: 6.9, w: 13.333, h: 0.1, fill: { color: ORANGE } });
  s.addText("Medieanalyse", { x: 0.8, y: 2.3, w: 11.7, h: 1.0, fontFace: FONT, fontSize: 20, color: ORANGE, bold: true, charSpacing: 2 });
  s.addText(metrics.org_name, { x: 0.8, y: 2.8, w: 11.7, h: 1.3, fontFace: FONT, fontSize: 44, color: WHITE, bold: true });
  s.addText(metrics.period_label_da, { x: 0.8, y: 4.1, w: 11.7, h: 0.5, fontFace: FONT, fontSize: 18, color: "CFCFCF" });
  s.addText("Datakilde: Overskrift.dk", { x: 0.8, y: 6.5, w: 6, h: 0.4, fontFace: FONT, fontSize: 12, color: "999999" });
}

// ---------- Slide 2: KPIs ----------
{
  const s = bgSlide();
  s.addText("Overblik", { x: 0.6, y: 0.4, w: 8, h: 0.7, fontFace: FONT, fontSize: 28, bold: true, color: BLACK });
  const kpis = [
    ["Samlede omtaler", String(metrics.total)],
    ["Gns. pr. dag", String(metrics.avg_per_day)],
    ["Unikke kilder", String(metrics.unique_sources)],
    ["Kanaler i spil", String(metrics.unique_channels)],
    ["Analyseperiode", `${metrics.n_days} dage`],
  ];
  const n = kpis.length, cardW = 2.25, gap = 0.25, totalW = n * cardW + (n - 1) * gap, startX = (13.333 - totalW) / 2;
  kpis.forEach((kv, i) => {
    const x = startX + i * (cardW + gap);
    s.addShape("roundRect", { x, y: 2.3, w: cardW, h: 1.8, rectRadius: 0.12, fill: { color: WHITE }, shadow: makeShadow() });
    s.addText(kv[1], { x, y: 2.5, w: cardW, h: 0.9, align: "center", fontFace: FONT, fontSize: 30, bold: true, color: ORANGE });
    s.addText(kv[0], { x: x + 0.1, y: 3.4, w: cardW - 0.2, h: 0.6, align: "center", fontFace: FONT, fontSize: 12, color: MUTED });
  });
  s.addText(`Søgeterm: "${metrics.searchterm_display}"`, { x: 0.6, y: 6.7, w: 12, h: 0.4, fontFace: FONT, fontSize: 12, color: MUTED, italic: true });
}

// ---------- Slide 3: Timeline ----------
{
  const s = bgSlide();
  s.addText("Omtaler over tid", { x: 0.6, y: 0.4, w: 8, h: 0.7, fontFace: FONT, fontSize: 28, bold: true, color: BLACK });
  const subByGran = {
    hour: "Antal omtaler pr. time i analyseperioden",
    day: "Antal omtaler pr. dag i analyseperioden",
    week: "Antal omtaler pr. uge i analyseperioden",
    month: "Antal omtaler pr. måned i analyseperioden",
  };
  s.addText(subByGran[metrics.timeline.granularity] || subByGran.day, { x: 0.6, y: 1.0, w: 10, h: 0.4, fontFace: FONT, fontSize: 13, color: MUTED });
  s.addChart(pres.ChartType.bar, [{ name: "Omtaler", labels: metrics.timeline.labels, values: metrics.timeline.values }], {
    x: 0.5, y: 1.6, w: 12.3, h: 5.4,
    barDir: "col",
    chartColors: [ORANGE],
    catAxisLabelFontSize: metrics.timeline.labels.length > 20 ? 8 : 10,
    catAxisLabelColor: MUTED,
    valAxisLabelFontSize: 9,
    showLegend: false,
    showTitle: false,
    catAxisLabelRotate: metrics.timeline.labels.length > 20 ? 45 : 0,
    barGapWidthPct: 20,
  });
}

// ---------- Slide 4: Channel distribution ----------
{
  const s = bgSlide();
  s.addText("Kanalfordeling", { x: 0.6, y: 0.4, w: 8, h: 0.7, fontFace: FONT, fontSize: 28, bold: true, color: BLACK });
  s.addChart(pres.ChartType.doughnut, [{ name: "Kanaler", labels: metrics.channels.labels, values: metrics.channels.values }], {
    x: 0.6, y: 1.3, w: 6.5, h: 5.8,
    chartColors: PALETTE,
    showLegend: false,
    dataLabelColor: WHITE, showValue: true, showPercent: true, dataLabelFontSize: 10,
  });
  // Bevidst kun ÉN signaturforklaring på denne slide: den håndbyggede liste
  // nedenfor, som viser antal + procent. Slå IKKE chartets indbyggede
  // showLegend til igen — det giver en anden, tallø legend ved siden af
  // denne og duplikerer forklaringen (set i praksis, rettet 2026-08-20).
  const total = metrics.channels.values.reduce((a, b) => a + b, 0);
  let y = 1.5;
  s.addText("Fordeling", { x: 7.6, y: 1.1, w: 5, h: 0.4, fontFace: FONT, fontSize: 14, bold: true, color: BLACK });
  metrics.channels.labels.forEach((lbl, i) => {
    const val = metrics.channels.values[i];
    const pct = Math.round((val / total) * 100);
    s.addShape("rect", { x: 7.6, y: y + 0.06, w: 0.18, h: 0.18, fill: { color: PALETTE[i % PALETTE.length] } });
    s.addText(`${lbl}  ${val} (${pct}%)`, { x: 7.9, y: y, w: 4.5, h: 0.3, fontFace: FONT, fontSize: 12, color: BLACK });
    y += 0.38;
  });
}

// ---------- Slide 5: Top 10 sources ----------
{
  const s = bgSlide();
  s.addText("Top 10 kilder", { x: 0.6, y: 0.4, w: 8, h: 0.7, fontFace: FONT, fontSize: 28, bold: true, color: BLACK });
  const labels = metrics.top_sources.map(x => x.label.length > 45 ? x.label.slice(0, 45) + "…" : x.label);
  const values = metrics.top_sources.map(x => x.value);
  s.addChart(pres.ChartType.bar, [{ name: "Omtaler", labels, values }], {
    x: 0.5, y: 1.2, w: 12.3, h: 5.9,
    barDir: "bar",
    chartColors: [BLUE],
    catAxisLabelFontSize: 10, catAxisLabelColor: MUTED, valAxisLabelFontSize: 10,
    showLegend: false, showTitle: false,
    dataLabelPosition: "outEnd", showValue: true, dataLabelFontSize: 10,
  });
}

// ---------- Slide 6: Top 5 themes — waffle-diagram (andel af SAMLEDE omtaler) ----------
// Waffle-gitteret erstatter det tidligere kort-layout: hvert af de 100 felter
// er 1% af metrics.total (ikke kun af summen af top 5), og "øvrige" indgår
// altid som en 6. — grå — kategori, så gitteret altid fylder et fast 10x10-
// mønster uanset hvordan de enkelte andele runder af.
{
  const s = bgSlide();
  s.addText("Top 5 mærkesager", { x: 0.6, y: 0.35, w: 9, h: 0.6, fontFace: FONT, fontSize: 26, bold: true, color: BLACK });
  s.addText("Hvert felt = 1% af samtlige omtaler i perioden — ikke kun af summen af top 5.", { x: 0.6, y: 0.9, w: 10, h: 0.35, fontFace: FONT, fontSize: 12.5, color: MUTED });

  const topics = topicsData.topics; // præcis 5, jf. SKILL.md trin 2
  const counts = topics.map((t) => t.count);
  const restCount = Math.max(0, metrics.total - counts.reduce((a, b) => a + b, 0));
  const allCounts = counts.concat([restCount]);
  const colors = topics.map((_, i) => PALETTE[i % PALETTE.length]).concat([REST_GREY]);
  const squares = apportionSquares(allCounts, 100);

  const seq = [];
  colors.forEach((c, i) => { for (let k = 0; k < squares[i]; k++) seq.push(c); });

  // ---- Waffle-gitter: 100 native rektangler, 10x10 ----
  const gridX = 0.7, gridY = 1.65, cell = 0.335, gap = 0.045;
  seq.forEach((color, i) => {
    const col = i % 10, row = Math.floor(i / 10);
    s.addShape("roundRect", {
      x: gridX + col * (cell + gap), y: gridY + row * (cell + gap),
      w: cell, h: cell, rectRadius: 0.03, fill: { color }, line: { type: "none" },
    });
  });
  const gridSide = 10 * cell + 9 * gap;
  s.addText(
    "Hvert felt = 1% af de samlede omtaler. Læses række for række, øverst til venstre.",
    { x: gridX, y: gridY + gridSide + 0.18, w: gridSide, h: 0.6, fontFace: FONT, fontSize: 9.5, color: MUTED }
  );

  // ---- Legende: de 5 mærkesager + "øvrige" ----
  const legendX = gridX + gridSide + 0.55;
  const legendW = 13.333 - 0.6 - legendX;
  const rowH = 0.86;
  let ly = 1.55;
  const rows = topics.map((t, i) => ({ color: PALETTE[i % PALETTE.length], title: t.title, desc: t.desc, count: t.count }));
  rows.push({ color: REST_GREY, title: "Øvrige omtaler", desc: "Alt andet i datasættet: enkeltstående nyheder, opslag uden for top 5, sociale medier m.m.", count: restCount });
  rows.forEach((r, i) => {
    const pct = metrics.total ? Math.round((r.count / metrics.total) * 1000) / 10 : 0;
    const pctStr = pct.toFixed(1).replace(".", ",") + "%";
    s.addShape("rect", { x: legendX, y: ly + 0.06, w: 0.16, h: 0.16, fill: { color: r.color }, line: { type: "none" } });
    s.addText(r.title, { x: legendX + 0.3, y: ly - 0.06, w: legendW - 1.5, h: 0.3, fontFace: FONT, fontSize: 12.5, bold: true, color: BLACK, margin: 0 });
    s.addText(r.desc, { x: legendX + 0.3, y: ly + 0.24, w: legendW - 1.5, h: 0.42, fontFace: FONT, fontSize: 9.5, color: MUTED, margin: 0 });
    s.addText(pctStr, { x: legendX + legendW - 1.15, y: ly - 0.06, w: 1.15, h: 0.3, align: "right", fontFace: FONT, fontSize: 13, bold: true, color: BLACK, margin: 0 });
    s.addText(`${r.count} omtaler`, { x: legendX + legendW - 1.15, y: ly + 0.19, w: 1.15, h: 0.25, align: "right", fontFace: FONT, fontSize: 9, color: MUTED, margin: 0 });
    if (i < rows.length - 1) {
      s.addShape("line", { x: legendX, y: ly + rowH - 0.1, w: legendW, h: 0, line: { color: GREY, width: 0.75 } });
    }
    ly += rowH;
  });
}

// ---------- Slide 7: Selected mentions (last slide — includes logo) ----------
{
  const s = bgSlide();
  s.addText("Udvalgte omtaler", { x: 0.6, y: 0.4, w: 8, h: 0.7, fontFace: FONT, fontSize: 28, bold: true, color: BLACK });
  s.addText("De mest markante medier i perioden", { x: 0.6, y: 1.0, w: 10, h: 0.4, fontFace: FONT, fontSize: 13, color: MUTED });
  let y = 1.6;
  metrics.notable5.forEach((m) => {
    s.addShape("roundRect", { x: 0.6, y: y, w: 12.1, h: 0.85, rectRadius: 0.06, fill: { color: WHITE }, shadow: makeShadow() });
    s.addText(m.title, { x: 0.85, y: y + 0.08, w: 11.6, h: 0.4, fontFace: FONT, fontSize: 13, bold: true, color: BLACK });
    s.addText(`${m.src}  ·  ${m.date_da}`, { x: 0.85, y: y + 0.48, w: 11.6, h: 0.3, fontFace: FONT, fontSize: 10, color: MUTED });
    y += 1.0;
  });
  // Overskrift-logo i nederste højre hjørne af den sidste slide (intet separat afslutningsslide)
  if (logo && fs.existsSync(logo)) {
    s.addImage({ path: logo, x: 11.3, y: 7.05, w: 1.5, h: 0.225 });
  }
}

pres.writeFile({ fileName: out }).then(() => {
  console.log(`PPTX skrevet til ${out}`);
});
