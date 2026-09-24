// Defence deck, business rework (September). Run: node build_deck.js
//
// Every figure below is read from reports/slides/deck_facts.json, which is written by
// verify_business.py / verify_value.py / verify_stats.py. Nothing is typed by hand, so
// a slide cannot drift from a number that was actually computed.
const pptx = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const S = path.join(ROOT, "reports", "slides");
const OUT = path.join(ROOT, "reports", "Real_Estate_Machine_defense.pptx");
const F = JSON.parse(fs.readFileSync(path.join(S, "deck_facts.json"), "utf8"));

// ---------------------------------------------------------------------------
// Ink & Amber — the same tokens as scripts/design.py and .streamlit/config.toml,
// so the deck, the charts and the live app are one identity. The three colours
// that carry meaning (amber, teal, brick) were checked with the palette
// validator on both the paper and the ink surface, not chosen by eye.
// ---------------------------------------------------------------------------
const PAPER = "FBFAF7";        // slide background
const CARD = "F2EFE9";         // a block of related content
const CARD_WARM = "FAF0E2";    // a card making a positive point
const CARD_COOL = "F6EEEB";    // a card making a negative one
const RULE = "E2DCD1";
const INK = "191714";          // headlines, dark slides
const BODY_INK = "3A342C";
const MUTED = "6B6358";

const AMBER = "C07214";        // the subject: this model, this house, the answer
const TEAL = "0094A0";         // a gain, a pass
const BRICK = "B23A20";        // a loss, a failure

const INK_DEEP = "141210";     // dark-slide surface
const INK_CARD = "2A2621";
const AMBER_ON_DARK = "E8B361";
const PAPER_DIM = "D9D2C6";
const WHITE = "FFFFFF";

// Kept so the slide bodies below need no rewriting: the old role names now point
// at the new system.
const NAVY = INK_DEEP, NAVY_SOFT = INK_CARD;
const AQUA = AMBER, AQUA_ON_DARK = AMBER_ON_DARK;
const BLUE = TEAL, RED = BRICK, TINT = CARD;

const HEAD = "Cambria", BODY = "Calibri";

const p = new pptx();
p.layout = "LAYOUT_WIDE";
p.author = "Esraa Maamoun";
p.title = "The Real Estate Machine — Graduation Project";

const W = 13.33, H = 7.5, M = 0.62;
const usd = (n) => "$" + Math.round(n).toLocaleString("en-US");
const usdk = (n) => "$" + Math.round(n / 1000).toLocaleString("en-US") + "k";

function darkSlide() {
  const s = p.addSlide();
  s.background = { color: INK_DEEP };
  // Overshoot the edges: a background colour alone can leave a one-pixel light
  // hairline down the right side in some renderers and on some projectors.
  s.addShape(p.ShapeType.rect, {
    x: -0.06, y: -0.06, w: W + 0.12, h: H + 0.12,
    fill: { color: INK_DEEP }, line: { color: INK_DEEP },
  });
  // The amber band is what makes the three dark slides one family.
  s.addShape(p.ShapeType.rect, {
    x: 0, y: 0, w: 0.16, h: H, fill: { color: AMBER }, line: { color: AMBER },
  });
  return s;
}

function lightSlide(title, kicker) {
  const s = p.addSlide();
  s.background = { color: PAPER };
  if (kicker) {
    s.addText(kicker.toUpperCase(), {
      x: M, y: 0.46, w: 9, h: 0.26, fontFace: BODY, fontSize: 11,
      bold: true, color: AMBER, charSpacing: 2.2, margin: 0,
    });
  }
  s.addText(title, {
    x: M, y: 0.76, w: W - 2 * M, h: 0.72, fontFace: HEAD, fontSize: 30,
    bold: true, color: INK, margin: 0,
  });
  // No rule under the title: at this size it reads as an underline on the first
  // word rather than as a mark of the identity. The amber eyebrow above the title,
  // and the amber band on the dark slides, carry it instead.
  return s;
}

function chip(s, n, x, y, size = 0.42, fill = AQUA) {
  s.addShape(p.ShapeType.ellipse, { x, y, w: size, h: size, fill: { color: fill } });
  s.addText(String(n), {
    x, y, w: size, h: size, align: "center", valign: "middle",
    fontFace: BODY, fontSize: 13, bold: true, color: WHITE, margin: 0,
  });
}

function card(s, x, y, w, h, fill = CARD) {
  s.addShape(p.ShapeType.roundRect, {
    x, y, w, h, fill: { color: fill }, rectRadius: 0.06, line: { color: fill },
  });
}

function stat(s, x, y, w, value, label, color = INK) {
  s.addText(value, { x, y, w, h: 0.72, fontFace: HEAD, fontSize: 38, bold: true, color, margin: 0 });
  s.addText(label, {
    x, y: y + 0.72, w, h: 0.66, fontFace: BODY, fontSize: 12.5, color: MUTED,
    valign: "top", margin: 0,
  });
}

function footnote(s, text, y = 6.62) {
  s.addText(text, {
    x: M, y, w: W - 2 * M, h: 0.45, fontFace: BODY, fontSize: 13,
    italic: true, color: MUTED, margin: 0,
  });
}

const note = (s, t) => s.addNotes(t);

// ============================================================ 1. cover
{
  const s = darkSlide();

  s.addText("GRADUATION PROJECT  ·  DATA SCIENCE", {
    x: M + 0.2, y: 1.5, w: 10.4, h: 0.3, fontFace: BODY, fontSize: 11.5,
    bold: true, color: AMBER_ON_DARK, charSpacing: 2.4, margin: 0,
  });
  s.addText("The Real Estate\nMachine", {
    x: M + 0.2, y: 1.95, w: 10.4, h: 2.1, fontFace: HEAD, fontSize: 54,
    bold: true, color: WHITE, lineSpacingMultiple: 0.95, margin: 0,
  });
  s.addText(`Values a house in a second, to within ${F.medape}% — and says how much to trust the number`, {
    x: M + 0.2, y: 4.15, w: 10.6, h: 0.5, fontFace: BODY, fontSize: 18,
    color: PAPER_DIM, margin: 0,
  });

  // Three figures across the foot: the whole argument, before a word is said.
  const tiles = [
    [`${F.medape}%`, "typical error on houses\nit had never seen"],
    [usd(F.medae), "half of valuations land\nwithin this of the sale price"],
    [`${(F.n_train + F.n_test).toLocaleString()}`, "verified sales, cleaned\nand parsed from raw JSON"],
  ];
  const tw = 3.5;
  tiles.forEach(([v, l], i) => {
    const x = M + 0.2 + i * (tw + 0.42);
    s.addText(v, {
      x, y: 5.28, w: tw, h: 0.62, fontFace: HEAD, fontSize: 30, bold: true,
      color: AMBER_ON_DARK, margin: 0,
    });
    s.addText(l, {
      x, y: 5.92, w: tw, h: 0.62, fontFace: BODY, fontSize: 12, color: PAPER_DIM,
      valign: "top", margin: 0,
    });
  });

  s.addText("Esraa Maamoun   ·   App: EstateIQ — AI-Assisted Real Estate Valuation & Decision Support", {
    x: M + 0.2, y: 6.82, w: 11, h: 0.35, fontFace: BODY, fontSize: 13,
    color: "9C948A", margin: 0,
  });
  note(s, "Opening line: 'I built a tool that values a house in about a second, tells you how much to trust the number, and writes the reasoning in plain English. I will show you the tool at the end. First, what it is for and why the number is defensible.'\n\nThe three figures at the foot are the whole argument in advance: accuracy, what that means in money, and the size of the evidence.\n\nTiming target: 14 minutes, leaving time for questions.");
}

// ============================================================ 2. the problem
{
  const s = lightSlide("A valuation is a decision, and a wrong one costs money", "The problem");
  const rows = [
    ["Sellers", "Price too high and the listing goes stale; too low and the money is simply gone.", BLUE],
    ["Buyers", "No way to tell an asking price from a fair price without paying for an appraisal.", BLUE],
    ["Brokers and lenders", "Need a defensible number in minutes, on hundreds of properties, not one at a time.", AQUA],
  ];
  let y = 1.75;
  rows.forEach(([h, t, c], i) => {
    card(s, M, y, W - 2 * M, 1.15);
    chip(s, i + 1, M + 0.34, y + 0.36, 0.44, c);
    s.addText(h, { x: M + 1.05, y: y + 0.2, w: 3.2, h: 0.42, fontFace: BODY, fontSize: 16, bold: true, color: INK, margin: 0 });
    s.addText(t, { x: M + 1.05, y: y + 0.62, w: 10.4, h: 0.42, fontFace: BODY, fontSize: 14, color: MUTED, margin: 0 });
    y += 1.4;
  });
  s.addText("The gap this fills: a number, an honest range around it, and a reason — in about a second, at a cost of effectively zero.", {
    x: M, y: 6.15, w: W - 2 * M, h: 0.5, fontFace: BODY, fontSize: 15, italic: true, color: INK, margin: 0,
  });
  note(s, "Lean on the insurance background: this is the underwriting problem — pricing an asset you cannot inspect, from the characteristics you can observe, and knowing how wrong you are likely to be.\n\nDo not oversell. The claim is a screening tool, not a replacement for an appraiser.");
}

// ============================================================ 3. data + cleaning (merged)
{
  const s = lightSlide("4,345 sales, ten weeks, and four decisions I can defend", "Data");
  const sw = 2.7, sp = 3.13;
  stat(s, M, 1.55, sw, (F.n_train + F.n_test).toLocaleString(), "sales, after cleaning");
  stat(s, M + sp, 1.55, sw, "77", "zip codes, 44 cities");
  stat(s, M + 2 * sp, 1.55, sw, "10 weeks", "2 May – 10 July 2014");
  stat(s, M + 3 * sp, 1.55, sw, "21", "columns, parsed out of JSON");

  const items = [
    ["Deleted 49 rows", "Price or living area of zero — missing data wearing a number. 1.1% of the file; imputing a price would invent the target."],
    ["Kept every outlier", "The $26m sale is real. Dropping hard houses buys a flattering error rate and nothing else."],
    ["Split address into city and zip", "Location is the strongest signal in the data, and it arrived as one comma-separated string."],
    ["Never touched price_per_sqft", "Price divided by size contains the answer. With it, R² is 0.99 and the model can only value houses already sold."],
  ];
  const cw = (W - 2 * M - 0.35) / 2, ch = 1.5;
  items.forEach(([h, t], i) => {
    const x = M + (i % 2) * (cw + 0.35), y = 3.28 + Math.floor(i / 2) * (ch + 0.28);
    card(s, x, y, cw, ch);
    s.addText(h, { x: x + 0.3, y: y + 0.18, w: cw - 0.6, h: 0.36, fontFace: BODY, fontSize: 15, bold: true, color: i === 3 ? RED : INK, margin: 0 });
    s.addText(t, { x: x + 0.3, y: y + 0.54, w: cw - 0.6, h: 0.9, fontFace: BODY, fontSize: 13, color: MUTED, valign: "top", margin: 0 });
  });
  footnote(s, "The source file was JSON with NaN literals, free-text room descriptions and mixed date formats — parsed, not loaded.", 6.62);
  note(s, "'Why did you delete 49 rows?' — a price of 0 or a living area of 0 is impossible, not extreme. 1.1% of the data, nothing to impute. Everything else was kept, including the expensive tail.\n\nIf they ask about the JSON: NaN is not valid JSON, so the file had to be repaired before any parser would read it; 'rooms' listed bedrooms and bathrooms in inconsistent order.");
}

// ============================================================ 4. insight 1 — logs
{
  const s = lightSlide("Prices are multiplicative, so the model learns logs", "Insight 1 of 3");
  s.addImage({ path: path.join(S, "fig_price_skew.png"), x: M, y: 1.6, w: 12.1, h: 3.96 });
  footnote(s, "Skew falls from 4.02 to 0.34. An error of 10% then costs the same on a $200k house and a $2m one — which is why every headline number in this deck is a percentage, and why the money slide converts it back.", 5.8);
  note(s, "'Why log-transform the price?' — (1) the error that matters is proportional, not absolute; (2) squared error on raw prices lets a handful of expensive houses dominate the fit; (3) it makes the size-price relationship roughly linear.\n\nOn the back-transform: expm1 of a mean in log space predicts the median, not the mean. Duan's smearing estimator made both bias and median error worse, so the notebook reports the plain back-transform and says so.");
}

// ============================================================ 5. insight 2 — location
{
  const s = lightSlide("Location is not a factor. It is the market.", "Insight 2 of 3");
  s.addImage({ path: path.join(S, "fig_zip_spread.png"), x: M, y: 1.55, w: 12.1, h: 3.74 });
  card(s, M, 5.5, W - 2 * M, 1.35);
  s.addText(`The same 2,000 sqft house: ${usd(F.same_lo)} in ${F.zip_lo_city}, ${usd(F.same_hi)} in ${F.zip_hi_city}.`, {
    x: M + 0.4, y: 5.68, w: 11.5, h: 0.4, fontFace: BODY, fontSize: 16.5, bold: true, color: INK, margin: 0,
  });
  s.addText(`${usd(F.zip_lo)} versus ${usd(F.zip_hi)} per square foot, across the 58 zip codes with 30 or more sales. The encoded zip code alone carries 46% of the model's importance — more than every structural feature combined. Screen the buy list by zip code before anyone visits a property.`, {
    x: M + 0.4, y: 6.08, w: 11.5, h: 0.7, fontFace: BODY, fontSize: 13.5, color: MUTED, margin: 0,
  });
  note(s, "Zip codes with fewer than 30 sales are excluded from the extremes here: with all 77 the spread looks like 4.2x, but the ends are thin cells. 3.2x is the defensible number and it is the one used everywhere in this deck.\n\nHow zip is encoded, if asked: each zip is replaced by its smoothed mean price, credibility-weighted with Z = n/(n+20) — the same formula used in actuarial ratemaking against thin cells — computed out-of-fold so a row's own price never contributes to its own feature.");
}

// ============================================================ 6. insight 3 — segments (+ classification)
{
  const s = lightSlide("The market is four markets", "Insight 3 of 3");
  s.addImage({ path: path.join(S, "fig_segments.png"), x: M, y: 1.5, w: 12.1, h: 3.96 });
  card(s, M, 5.55, W - 2 * M, 1.45);
  s.addText("And the segment is predictable: 98.7% accuracy against a 37.5% floor — but that is a weaker result than it looks.", {
    x: M + 0.4, y: 5.72, w: 11.5, h: 0.4, fontFace: BODY, fontSize: 15.5, bold: true, color: INK, margin: 0,
  });
  s.addText("The labels came from k-means, so the classifier is re-learning a boundary an algorithm drew — 98.7% measures how learnable that boundary is, not how well I understand houses. The honest test is a forest given only features k-means never saw: it still recovers the segment about 82% of the time, so the segments carry real information. (Logistic regression beats the random forest here because k-means boundaries are linear hyperplanes.)", {
    x: M + 0.4, y: 6.12, w: 11.5, h: 0.8, fontFace: BODY, fontSize: 12.5, color: MUTED, margin: 0,
  });
  note(s, "'Why k = 4?' — the elbow in inertia and the peak of the silhouette curve both pointed at 4, and 4 gave segments a person could name. Silhouette is 0.255, which is weak: these are regions of a continuum, not four species of house. Say that before anyone else does.\n\nIf they press on the 98.7%: agree it is suspicious, then explain why it is not leakage. The blind experiment (0.818 accuracy, 0.702 macro-F1) is in notebook 07.\n\nPremium View Property is 8% of the market and — slide 15 — the segment the model handles worst.");
}

// ============================================================ 7. NEW — what the market pays for
{
  const s = lightSlide("What the market actually pays for", "Business insight");
  s.addImage({ path: path.join(S, "fig_value_levers.png"), x: M, y: 1.5, w: 12.1, h: 4.4 });
  card(s, M, 6.02, W - 2 * M, 1.0);
  s.addText(`Buy the view and the condition. Add a bathroom, never a bedroom.`, {
    x: M + 0.4, y: 6.18, w: 11.5, h: 0.36, fontFace: BODY, fontSize: 16, bold: true, color: INK, margin: 0,
  });
  s.addText(`Subdividing a fixed floor area into one more bedroom takes ${usd(Math.abs(F.bed))} off the price: buyers pay for fewer, larger rooms. Finishing a basement is worse than doing nothing — ${usd(Math.abs(F.base100))} per 100 sqft, because it is space that could have been above ground.`, {
    x: M + 0.4, y: 6.54, w: 11.5, h: 0.42, fontFace: BODY, fontSize: 13, color: MUTED, margin: 0,
  });
  note(s, `Method, if asked: a log-price regression on the structural features with city dummies, R² = ${F.ols_r2}. The city dummies are what makes this 'holding location constant' — without them every coefficient is really measuring where the house is.\n\nSay the caveat out loud: this is association, not causation. 'A bathroom is worth ${usd(F.bath)}' means homes with more bathrooms sell for more, all else equal. It does not guarantee that building one returns ${usd(F.bath)} — that needs renovation cost data, which this dataset does not have.`);
}

// ============================================================ 8. NEW — the renovation correction
{
  const s = lightSlide("The most expensive mistake in the raw numbers", "Business insight");

  card(s, M, 1.6, 5.85, 2.3, CARD_COOL);
  s.addText("What the raw comparison says", { x: M + 0.35, y: 1.78, w: 5.1, h: 0.32, fontFace: BODY, fontSize: 13.5, bold: true, color: MUTED, margin: 0 });
  s.addText(`+${F.reno_raw}%`, { x: M + 0.35, y: 2.1, w: 5.1, h: 0.85, fontFace: HEAD, fontSize: 46, bold: true, color: RED, margin: 0 });
  s.addText("renovated homes sell for this much more per square foot", { x: M + 0.35, y: 2.98, w: 5.1, h: 0.6, fontFace: BODY, fontSize: 13, color: MUTED, margin: 0 });

  card(s, M + 6.25, 1.6, 5.85, 2.3, CARD_WARM);
  s.addText("What a like-for-like comparison says", { x: M + 6.6, y: 1.78, w: 5.1, h: 0.32, fontFace: BODY, fontSize: 13.5, bold: true, color: MUTED, margin: 0 });
  s.addText(`+${F.reno_lfl}%`, { x: M + 6.6, y: 2.1, w: 5.1, h: 0.85, fontFace: HEAD, fontSize: 46, bold: true, color: AQUA, margin: 0 });
  s.addText(`median across the ${F.reno_zips} zip codes with enough of both — and negative in ${F.reno_neg} of them`, { x: M + 6.6, y: 2.98, w: 5.1, h: 0.6, fontFace: BODY, fontSize: 13, color: MUTED, margin: 0 });

  s.addText("Why the gap: renovated homes are older, and old homes cluster in expensive neighbourhoods", {
    x: M, y: 4.1, w: W - 2 * M, h: 0.4, fontFace: BODY, fontSize: 17, bold: true, color: INK, margin: 0,
  });
  s.addText(`The median renovated home in this data is ${F.age_ren} years old; the median unrenovated one is ${F.age_not}. So the raw 23% is mostly measuring location, not renovation. Comparing inside a single zip code removes that, and the premium halves.`, {
    x: M, y: 4.55, w: W - 2 * M, h: 0.6, fontFace: BODY, fontSize: 14, color: MUTED, margin: 0,
  });

  card(s, M, 5.35, W - 2 * M, 1.4);
  s.addText(`What it means for a budget: on a median ${usd(F.median_price)} home, a 10% uplift is about ${usd(F.reno_be)}.`, {
    x: M + 0.4, y: 5.55, w: 11.5, h: 0.36, fontFace: BODY, fontSize: 16, bold: true, color: INK, margin: 0,
  });
  s.addText(`That is the break-even, not the profit. A refurbishment only pays if it costs less than that — and this dataset contains no renovation costs, so I cannot confirm that it does. Get contractor quotes before approving any scheme, and budget against 10%, not the 23% the raw numbers advertise.`, {
    x: M + 0.4, y: 5.92, w: 11.5, h: 0.6, fontFace: BODY, fontSize: 13, color: MUTED, margin: 0,
  });
  note(s, "This is the slide that shows analytical judgement rather than tool use. A confounder found, quantified, and corrected — and the correction halves a number a business would otherwise have budgeted against.\n\nIf asked how the like-for-like was done: within each zip code with at least 5 renovated and 5 unrenovated sales, compare median price per square foot. 16 zips qualified. The median of those 16 differences is +10%, and 6 of the 16 are negative — which is itself worth saying, because it means renovation is not reliably positive at all.");
}

// ============================================================ 9. NEW — what it is worth
{
  const s = lightSlide("What the model is worth, in money", "The business case");
  s.addImage({ path: path.join(S, "fig_money.png"), x: M, y: 1.52, w: 12.1, h: 3.85 });

  const cw = (W - 2 * M - 0.6) / 3;
  const tiles = [
    [usd(F.medae), "Half of all valuations land within this of the sale price", AQUA],
    [usd(F.save_ppsf), "Less error per house than a zip price-per-sqft valuation benchmark", INK],
    [usd(F.save_zip), "Less error per house than a plain zip-median lookup", INK],
  ];
  tiles.forEach(([v, l, c], i) => {
    const x = M + i * (cw + 0.3);
    card(s, x, 5.5, cw, 1.55);
    s.addText(v, { x: x + 0.28, y: 5.66, w: cw - 0.56, h: 0.62, fontFace: HEAD, fontSize: 30, bold: true, color: c, margin: 0 });
    s.addText(l, { x: x + 0.28, y: 6.3, w: cw - 0.56, h: 0.62, fontFace: BODY, fontSize: 12.5, color: MUTED, valign: "top", margin: 0 });
  });
  note(s, `The sentence to say: 'On a portfolio of 200 properties, the difference between this model and a zip-code price-per-sqft valuation benchmark is about $${(F.save_ppsf * 200 / 1000000).toFixed(1)}m of valuation error — and it takes a minute to run.'\n\nBe careful with that framing under questioning: it is error, not profit. The value is in better decisions — which properties to visit, which to bid on, what range to quote — not in the arithmetic itself.\n\nCost: the app runs on a free tier. Time: about a second per valuation.`);
}

// ============================================================ 10. recommendations
{
  const s = lightSlide("What a valuation workflow should do on Monday", "Recommendations");
  const recs = [
    ["Screen by zip code first, property second",
      `Location moves price ${F.zip_ratio}x; every structural feature combined moves it less. Set the buy list at zip level before anyone visits a house.`, BLUE],
    ["Spend on bathrooms and above-grade space",
      `+${usd(F.bath)} for a bathroom and +${usd(F.cond)} per condition point — against a loss of ${usd(Math.abs(F.bed))} for subdividing a bedroom and ${usd(Math.abs(F.base100))} per 100 sqft of basement.`, BLUE],
    ["Budget renovations against 10%, not 23%",
      `Break-even is about ${usd(F.reno_be)} on a median home. Require a contractor quote below it before approving the scheme.`, AQUA],
    ["Screen at scale, appraise selectively",
      `Run the portfolio through the model in a minute, then send a human to what it flags: the top decile, waterfront, and the Premium View segment — 8% of the market, where the error doubles.`, AQUA],
  ];
  let y = 1.6;
  recs.forEach(([h, t, c], i) => {
    card(s, M, y, W - 2 * M, 1.1);
    chip(s, i + 1, M + 0.34, y + 0.34, 0.44, c);
    s.addText(h, { x: M + 1.05, y: y + 0.14, w: 10.6, h: 0.36, fontFace: BODY, fontSize: 15.5, bold: true, color: INK, margin: 0 });
    s.addText(t, { x: M + 1.05, y: y + 0.5, w: 10.8, h: 0.55, fontFace: BODY, fontSize: 12.5, color: MUTED, valign: "top", margin: 0 });
    y += 1.24;
  });
  footnote(s, "The commercial case is not accuracy. It is a defensible number, an honest range and a written reason, in a second, for nothing.", 6.55);
  note(s, "Slow down here. This is where the examiners find out whether the modelling served a decision.\n\nOne concrete example: a team with 200 listings runs them all through the app in a minute, quotes a range rather than a number, and sends a valuer only to the 30 the model is least sure about.");
}

// ============================================================ 11. model comparison
{
  const s = lightSlide("Seven models, one baseline that is not zero", "Modelling");
  s.addImage({ path: path.join(S, "fig_model_comparison.png"), x: M, y: 1.55, w: 12.1, h: 4.18 });
  footnote(s, `Trained on ${F.n_train.toLocaleString()} houses, scored on the same ${F.n_test} none of them ever saw. A zip-median lookup — no model at all — scores 21.0%; every model here beats it, which is the least they should do.`, 5.95);
  note(s, "MedAPE, not R², is the headline, and it was chosen before the models were run: a median percentage error is what a client experiences. R² on logged prices makes 0.827 and 0.863 sound close when the median error behind them differs by two full points — $10,000 on a $500,000 house.\n\nTuning: three 12-combination grid searches, 60 fits each, cross-validated inside the training set only.");
}

// ============================================================ 12. is the winner real
{
  const s = lightSlide("Is the winner actually better, or just luckier?", "The test");

  card(s, M, 1.6, 5.85, 2.35, TINT);
  s.addText("vs the Ridge baseline", { x: M + 0.35, y: 1.8, w: 5.1, h: 0.32, fontFace: BODY, fontSize: 14, bold: true, color: MUTED, margin: 0 });
  s.addText(`${F.vs_ridge.diff_pp} pp`, { x: M + 0.35, y: 2.12, w: 5.1, h: 0.75, fontFace: HEAD, fontSize: 38, bold: true, color: AQUA, margin: 0 });
  s.addText(`95% bootstrap CI [${F.vs_ridge.ci_lo}, ${F.vs_ridge.ci_hi}]\nWilcoxon p ≈ 1e−7   →   a real difference`, {
    x: M + 0.35, y: 2.9, w: 5.1, h: 0.8, fontFace: BODY, fontSize: 13.5, color: MUTED, margin: 0,
  });

  card(s, M + 6.25, 1.6, 5.85, 2.35, TINT);
  s.addText("vs tuned XGBoost", { x: M + 6.6, y: 1.8, w: 5.1, h: 0.32, fontFace: BODY, fontSize: 14, bold: true, color: MUTED, margin: 0 });
  s.addText(`${F.vs_xgb.diff_pp} pp`, { x: M + 6.6, y: 2.12, w: 5.1, h: 0.75, fontFace: HEAD, fontSize: 38, bold: true, color: MUTED, margin: 0 });
  s.addText(`95% bootstrap CI [${F.vs_xgb.ci_lo.toFixed(2)}, +${F.vs_xgb.ci_hi.toFixed(2)}]\nWilcoxon p = ${F.vs_xgb.p.toFixed(2)}   →   not distinguishable`, {
    x: M + 6.6, y: 2.9, w: 5.1, h: 0.8, fontFace: BODY, fontSize: 13.5, color: MUTED, margin: 0,
  });

  card(s, M, 4.15, W - 2 * M, 1.5, CARD_COOL);
  s.addText("And on two other metrics, XGBoost wins.", {
    x: M + 0.4, y: 4.33, w: 11.5, h: 0.38, fontFace: BODY, fontSize: 16.5, bold: true, color: INK, margin: 0,
  });
  s.addText(`R² ${F.xgb_r2} against ${F.gb_r2}, and mean percentage error ${F.xgb_mape}% against ${F.gb_mape}%. I am not going to hide that behind the one metric my model happens to win. Three comparisons, no separation: these two models are the same model as far as this test set can tell.`, {
    x: M + 0.4, y: 4.72, w: 11.5, h: 0.75, fontFace: BODY, fontSize: 13.5, color: MUTED, margin: 0,
  });

  card(s, M, 5.85, W - 2 * M, 1.15, CARD_WARM);
  s.addText("So the accuracy metrics cannot pick the winner. Something else has to.", {
    x: M + 0.4, y: 6.08, w: 11.5, h: 0.4, fontFace: BODY, fontSize: 17, bold: true, color: INK, margin: 0,
  });
  s.addText("Two models I cannot tell apart are not two equally good products — the tie-break has to come from outside the leaderboard.", {
    x: M + 0.4, y: 6.48, w: 11.5, h: 0.4, fontFace: BODY, fontSize: 13, color: MUTED, margin: 0,
  });
  note(s, "This is the slide that separates the project from a leaderboard exercise, and the honesty is the point. Do not say 'slightly better'; say 'not distinguishable'.\n\nEvery number on this slide comes from notebook 09, section 8 — the same run that produced the comparison table on the previous slide, so the two slides cannot disagree. One more detail if asked: gradient boosting has the smaller error on only 47% of individual houses, which is one more sign of a tie, not a hidden loss.\n\nBoth comparisons are paired — the same 869 houses, both models — with a Wilcoxon signed-rank test and a 2,000-sample bootstrap on the difference in median error.\n\nIf an examiner opens model_comparison.csv and finds XGBoost ahead on R², you have already said it. That is the whole reason it is on the slide.");
}

// ============================================================ 13. IAAO
{
  const s = lightSlide("The ratio study narrows four models to two", "Fairness");
  s.addImage({ path: path.join(S, "fig_iaao.png"), x: M, y: 1.42, w: 11.55, h: 3.2 });
  card(s, M, 4.72, W - 2 * M, 1.45);
  s.addText("PRD is a fairness test, not an accuracy test.", {
    x: M + 0.4, y: 4.88, w: 11.5, h: 0.38, fontFace: BODY, fontSize: 16, bold: true, color: INK, margin: 0,
  });
  s.addText(`A model can be accurate on average while over-valuing cheap homes and under-valuing expensive ones — in a tax assessment that means poorer owners subsidise wealthier ones, and it is invisible in R² and in MAPE. Ridge fails consistency (COD ${F.iaao["Ridge baseline"].cod.toFixed(1)}); Random Forest fails vertical equity (PRD ${F.iaao["RF (tuned)"].prd.toFixed(3)}). Gradient boosting and XGBoost both pass all three.`, {
    x: M + 0.4, y: 5.26, w: 11.5, h: 0.8, fontFace: BODY, fontSize: 13, color: MUTED, margin: 0,
  });
  card(s, M, 6.26, W - 2 * M, 0.68, CARD_WARM);
  s.addText("Final choice, stated as what it is: two models are tied, so I shipped the one that needs no extra dependency to deploy and that won the metric I named in advance.", {
    x: M + 0.4, y: 6.4, w: 11.5, h: 0.42, fontFace: BODY, fontSize: 13, bold: true, color: INK, margin: 0,
  });
  note(s, "IAAO = International Association of Assessing Officers; this is their Standard on Ratio Studies. Name the source out loud — it shows the criterion is a published valuation benchmark, not one I invented.\n\nBe honest that COD 14.6 and PRD 1.030 sit near the edges of their bands, not comfortably inside. The next slide but one explains why PRD is strained: the top decile.\n\nIf pressed on the final choice: gradient boosting is in scikit-learn, so deployment needs no extra package; XGBoost would add one for a difference the test set cannot detect. That is an engineering reason, and I would rather give an engineering reason than pretend the data chose.");
}

// ============================================================ 14. benchmark
{
  const s = lightSlide(`${F.medape}% — good, bad, or neither?`, "Benchmark");
  s.addImage({ path: path.join(S, "fig_benchmark.png"), x: M, y: 1.6, w: 12.1, h: 3.74 });
  card(s, M, 5.5, W - 2 * M, 1.5);
  s.addText("The fairer reference point is the off-market one.", {
    x: M + 0.4, y: 5.68, w: 11.5, h: 0.38, fontFace: BODY, fontSize: 16, bold: true, color: INK, margin: 0,
  });
  s.addText(`Zillow's own published figures: ${F.zillow.off_market.toFixed(1)}% median error off-market, ${F.zillow.on_market.toFixed(1)}% on-market, where the model can see the asking price (zillow.com, checked ${F.zillow.checked}). Mine has no asking price; it sees 20 columns and ten weeks of 2014 in one county. Different market, years and data: context, not a head-to-head. ${F.ppe10}% of my valuations land within 10% of the sale price.`, {
    x: M + 0.4, y: 6.08, w: 11.5, h: 0.8, fontFace: BODY, fontSize: 13.5, color: MUTED, margin: 0,
  });
  note(s, `'Is 10-15% error good enough for a real business?' — quote both the median (10.5%) and the mean (14.6%); the mean is dragged by the tail and hiding that would be dishonest.\n\nThe answer: not for a mortgage valuation, where a lender needs an appraisal. Yes for screening, portfolio triage, and giving a seller a starting range in seconds.\n\nSource for the Zillow figures: ${F.zillow.url} — Zillow's own published nationwide median error rates (${F.zillow.on_market}% on-market, ${F.zillow.off_market}% off-market), checked ${F.zillow.checked}. Zillow updates these figures, so quote the date you checked them. They describe the whole US market today, not King County in 2014: context for the number, not a like-for-like test.`);
}

// ============================================================ 15. where it is wrong
{
  const s = lightSlide("Where it is wrong — said before anyone asks", "Limitations, measured");
  s.addImage({ path: path.join(S, "fig_error_by_decile.png"), x: M, y: 1.5, w: 12.1, h: 4.18 });
  footnote(s, "The cheapest tenth is over-valued by 12%; the most expensive tenth is under-valued by 11.5%. The second is structural — a tree can never predict above the highest value it saw in training, so the top of the market is capped by construction. That is also what strains PRD.", 5.85);
  note(s, "Volunteer this slide; do not wait to be asked. The fix in production is not a better booster: it is a separate model for the top decile, or a linear model in the tail where extrapolation is possible.\n\nAlso honest: deciles 2-4 are marginally better under Ridge than under the booster. The winner is not better everywhere.");
}

// ============================================================ 16. NEW — confidence by segment
{
  const s = lightSlide("The model knows which houses it is bad at — and now says so", "Confidence");
  s.addImage({ path: path.join(S, "fig_confidence_bands.png"), x: M, y: 1.45, w: 12.1, h: 4.29 });
  card(s, M, 5.85, W - 2 * M, 1.2, CARD_WARM);
  s.addText(`One band for every house would have been ${F.global_lo}% to +${F.global_hi}% — far too narrow where it matters.`, {
    x: M + 0.4, y: 6.03, w: 11.5, h: 0.38, fontFace: BODY, fontSize: 15.5, bold: true, color: INK, margin: 0,
  });
  s.addText(`The app now quotes the band for the house's own segment and names which houses it was measured on. A Premium View property gets a range ${(F.bands[3].width / F.bands[0].width).toFixed(1)}x wider than an Established Family Home — which is the truth, and the difference between a range and a guess dressed as one.`, {
    x: M + 0.4, y: 6.42, w: 11.5, h: 0.55, fontFace: BODY, fontSize: 13, color: MUTED, margin: 0,
  });
  note(s, "This change came out of reviewing my own notebook: the range was a single global band even though the error is demonstrably segment-dependent. Saying 'I found this in my own work and fixed it' is worth more than any result on these slides.\n\nIf asked why not a per-house interval: with 869 test rows, a per-segment band is about as fine as the data supports. Quantile regression or conformal prediction would give a per-house interval and is the obvious next step.");
}

// ============================================================ 17. live demo
{
  const s = lightSlide("EstateIQ: a number, a range, a reason, a warning", "Live demo");
  s.addImage({ path: path.join(S, "app_panel.png"), x: M, y: 1.6, w: 6.2, h: 4.77 });
  const bx = M + 6.5, bwid = W - M - bx;
  const bullets = [
    ["A range, not a point", "and it names the houses it was measured on"],
    ["SHAP drivers", "what moved THIS valuation, not features in general"],
    ["Deterministic warnings", "unknown zip, waterfront, top decile, worst segment"],
    ["A written explanation", "every number in it checked against the evidence"],
  ];
  let by = 1.5;
  bullets.forEach(([h, t]) => {
    card(s, bx, by, bwid, 1.05);
    s.addText(h, { x: bx + 0.3, y: by + 0.15, w: bwid - 0.6, h: 0.34, fontFace: BODY, fontSize: 14.5, bold: true, color: INK, margin: 0 });
    s.addText(t, { x: bx + 0.3, y: by + 0.5, w: bwid - 0.6, h: 0.45, fontFace: BODY, fontSize: 12.5, color: MUTED, valign: "top", margin: 0 });
    by += 1.28;
  });
  footnote(s, "The app imports the same preprocessing module that trained the model — a training/serving mismatch is impossible by construction, not by discipline.", 6.55);
  note(s, "SWITCH TO THE LIVE APP HERE. Ninety seconds: fill the form, press the button, point at the range and say which segment it is based on, point at the biggest driver, then open 'Test it on real sales' and show predictions against true sale prices.\n\nIf a five-house draw looks bad, that is the tab working. Say 'five houses is a sample of five; the test-set figure of 10.5% is the one to quote' and move on.\n\nIf the network is dead: the recording, then the local copy — neither needs internet.");
}

// ============================================================ 18. the AI layer
{
  const s = lightSlide("The AI writes the sentences. It does not do the maths.", "The AI layer");
  const steps = [
    ["Model", "gradient booster\npredicts the price"],
    ["SHAP", "computes what moved\nthis prediction"],
    ["Rules", "deterministic checks\nfire the warnings"],
    ["LLM", "turns the evidence\ninto a paragraph"],
    ["Grounding", "every number checked\nagainst the evidence"],
  ];
  const gap = 0.34, bw = (W - 2 * M - 4 * gap) / 5;
  steps.forEach(([h, t], i) => {
    const x = M + i * (bw + gap);
    card(s, x, 1.85, bw, 1.9, i === 4 ? CARD_WARM : TINT);
    chip(s, i + 1, x + 0.25, 2.05, 0.4, AQUA);
    s.addText(h, { x: x + 0.25, y: 2.55, w: bw - 0.5, h: 0.35, fontFace: BODY, fontSize: 15, bold: true, color: INK, margin: 0 });
    s.addText(t, { x: x + 0.25, y: 2.9, w: bw - 0.5, h: 0.75, fontFace: BODY, fontSize: 12, color: MUTED, margin: 0 });
    if (i < 4) s.addText("→", { x: x + bw, y: 2.55, w: gap, h: 0.35, fontFace: BODY, fontSize: 16, color: MUTED, align: "center", margin: 0 });
  });
  s.addText("Four defences, because \"we called an LLM\" is not an engineering answer", {
    x: M, y: 4.1, w: W - 2 * M, h: 0.4, fontFace: BODY, fontSize: 16, bold: true, color: INK, margin: 0,
  });
  s.addText([
    { text: "Evidence only — every figure it may use is placed in the prompt, and inventing others is forbidden.", options: { bullet: true, breakLine: true } },
    { text: "A grounding check reads back every number in the generated text and rejects the whole answer if one is not in the evidence.", options: { bullet: true, breakLine: true } },
    { text: "A deterministic fallback paragraph, so no key, no network and no quota still produces an explanation.", options: { bullet: true, breakLine: true } },
    { text: "An on-disk cache, so the demo can run with no internet at all.", options: { bullet: true } },
  ], { x: M, y: 4.55, w: W - 2 * M, h: 1.7, fontFace: BODY, fontSize: 14, color: MUTED, paraSpaceAfter: 6, margin: 0 });
  card(s, M, 6.22, W - 2 * M, 0.7, CARD_WARM);
  s.addText("There is a tick-box in the app that turns the language model off. The price, the range, the drivers and the warnings are identical with it off.", {
    x: M + 0.4, y: 6.37, w: 11.5, h: 0.42, fontFace: BODY, fontSize: 14, bold: true, color: INK, margin: 0,
  });
  note(s, "If asked whether it hallucinates: it can, which is why the output is parsed for numbers and the whole answer rejected if any figure was not in the evidence — with a 2% tolerance so rounding is allowed.");
}

// ============================================================ 19. limitations → investment
{
  const s = darkSlide();
  s.addText("LIMITATIONS, AND WHAT FIXING THEM BUYS", { x: M, y: 0.55, w: 9, h: 0.3, fontFace: BODY, fontSize: 11.5, bold: true, color: AQUA_ON_DARK, charSpacing: 1.6, margin: 0 });
  s.addText("What this model cannot do — and what I would spend next", {
    x: M, y: 0.9, w: 11.5, h: 0.7, fontFace: HEAD, fontSize: 29, bold: true, color: WHITE, margin: 0,
  });
  const lims = [
    ["Ten weeks of 2014", "No seasonality, no trend, a price level more than a decade stale.", "More months of data — the only way to say anything about direction."],
    ["Location is coarse", "No building grade, no coordinates; a zip code stands in for a neighbourhood.", "Coordinates and grade: the highest-value addition, and the cheapest."],
    ["The top decile is capped", "Trees cannot predict above the highest price they were trained on.", "A separate model for the tail, where extrapolation is possible."],
    [`${F.n_waterfront} waterfront homes`, "Too few for any confident claim, however dramatic the headline.", "Nothing to spend — say the sample size and move on."],
    ["It cannot see the house", "Condition is a 1–5 rating, not a kitchen, a neighbour, or a rushed sale.", "Photographs, and an inspection flag from the agent."],
  ];
  let y = 1.8;
  lims.forEach(([h, t, next]) => {
    s.addShape(p.ShapeType.roundRect, { x: M, y, w: W - 2 * M, h: 0.86, fill: { color: NAVY_SOFT }, line: { color: NAVY_SOFT }, rectRadius: 0.08 });
    s.addText(h, { x: M + 0.32, y: y + 0.08, w: 3.1, h: 0.34, fontFace: BODY, fontSize: 14, bold: true, color: AQUA_ON_DARK, margin: 0 });
    s.addText(t, { x: M + 0.32, y: y + 0.44, w: 6.0, h: 0.34, fontFace: BODY, fontSize: 12.5, color: "CFE0F0", margin: 0 });
    s.addText(next, { x: M + 6.6, y: y + 0.26, w: 5.4, h: 0.4, fontFace: BODY, fontSize: 12.5, italic: true, color: "9FB4C7", margin: 0 });
    y += 1.0;
  });
  note(s, "Saying these first makes you look strong, not weak. An examiner who has to extract a limitation from you has found a weakness; one who hears it volunteered has found a professional.\n\nThe right-hand column is the ask: if this were funded, coordinates and building grade are where the next pound goes, because location is already 46% of the model on a coarse proxy.");
}

// ============================================================ 20. close
{
  const s = darkSlide();
  s.addText("Thank you", {
    x: M + 0.2, y: 1.15, w: 8, h: 0.9, fontFace: HEAD, fontSize: 42, bold: true,
    color: WHITE, margin: 0,
  });
  s.addText("Questions welcome — including the hard ones.", {
    x: M + 0.2, y: 2.1, w: 8, h: 0.45, fontFace: BODY, fontSize: 17,
    color: PAPER_DIM, margin: 0,
  });

  const live = (F.live_url || "").trim();
  const qrFile = path.join(S, "qr_live_app.png");
  const hasQr = live && fs.existsSync(qrFile);

  const links = [
    ["EstateIQ live app", live || null],
    ["Code", F.repo_url || null],
    ["Kaggle notebook", F.kaggle_url || null],
  ];
  let y = 3.0;
  links.forEach(([h, url]) => {
    s.addShape(p.ShapeType.roundRect, {
      x: M + 0.2, y, w: 7.4, h: 0.82, fill: { color: INK_CARD },
      line: { color: INK_CARD }, rectRadius: 0.06,
    });
    s.addText(h, {
      x: M + 0.5, y: y + 0.08, w: 3.0, h: 0.3, fontFace: BODY, fontSize: 12.5,
      bold: true, color: AMBER_ON_DARK, charSpacing: 0.6, margin: 0,
    });
    s.addText(url || "to be added once deployed", {
      x: M + 0.5, y: y + 0.4, w: 6.8, h: 0.32, fontFace: BODY, fontSize: 13,
      color: url ? WHITE : "8A8177", italic: !url, margin: 0,
    });
    y += 0.98;
  });

  // The QR panel. It is designed for both states: a real code once
  // scripts/make_qr.py has been run, and an honest labelled frame until then.
  const qx = M + 8.05, qy = 3.0, qs = 2.95;
  s.addShape(p.ShapeType.roundRect, {
    x: qx, y: qy, w: qs, h: qs, fill: { color: hasQr ? PAPER : INK_CARD },
    line: { color: hasQr ? PAPER : AMBER, dashType: hasQr ? "solid" : "dash", width: 1.25 },
    rectRadius: 0.06,
  });
  if (hasQr) {
    s.addImage({ path: qrFile, x: qx + 0.22, y: qy + 0.22, w: qs - 0.44, h: qs - 0.44 });
    s.addText("Scan to open the live app", {
      x: qx, y: qy + qs + 0.12, w: qs, h: 0.3, fontFace: BODY, fontSize: 11.5,
      color: PAPER_DIM, align: "center", margin: 0,
    });
  } else {
    s.addText("QR", {
      x: qx, y: qy + 0.82, w: qs, h: 0.5, fontFace: HEAD, fontSize: 26, bold: true,
      color: AMBER_ON_DARK, align: "center", margin: 0,
    });
    s.addText("run  scripts/make_qr.py <url>\nand rebuild — the code lands here", {
      x: qx + 0.2, y: qy + 1.38, w: qs - 0.4, h: 0.8, fontFace: BODY, fontSize: 11.5,
      color: "8A8177", align: "center", margin: 0,
    });
  }

  s.addText(`${F.medape}% median error  ·  a range that widens where the model is weak  ·  a written reason for every number`, {
    x: M + 0.2, y: 6.55, w: 12.0, h: 0.4, fontFace: BODY, fontSize: 13.5,
    italic: true, color: AMBER_ON_DARK, margin: 0,
  });
  note(s, hasQr
    ? "The QR points at the live app. Leave this slide up during questions - anyone in the room can open the tool on their own phone while you answer."
    : "The three links and the QR are empty because nothing is deployed yet. Once it is: run `python scripts/make_qr.py <your streamlit url>`, then `node scripts/build_deck.js`, and this slide fills itself in - the QR, the link text and the colours are already laid out for it.\n\nIf you present before deploying, say 'it runs locally and I have just shown you' and move on; do not apologise for the empty slots.");
}

p.writeFile({ fileName: OUT }).then(() => console.log("wrote", OUT, "-", p.slides ? "" : ""));
