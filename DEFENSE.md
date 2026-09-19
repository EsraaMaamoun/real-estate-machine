# Presentation, rehearsal, and the questions

The deck is `reports/Real_Estate_Machine_defense.pptx` — 20 slides, speaker notes on every
one. This file holds what the deck cannot: the timing, the demo script, and the answers.

*Revised September 2026, after re-running every number against the current `Models/`
artifacts. Two claims from the August version were wrong and are corrected below — see
**The two corrections** before you rehearse.*

---

## The two corrections

**1. Two models pass the IAAO ratio study, not one.** The August deck said gradient
boosting was the only model to pass median ratio, COD and PRD together. Your own executed
notebook 09 shows XGBoost passing all three as well (COD 14.42, PRD 1.0297). If you say
"the only one" in the room and an examiner opens the notebook, you lose the slide and some
credibility with it. The deck now says what is true: **the ratio study eliminates Ridge
(COD 16.87) and Random Forest (PRD 1.043), and leaves two survivors.**

**2. XGBoost beats the shipped model on two metrics.** R² 0.8668 against 0.8627, and mean
percentage error 14.38% against 14.58%. Gradient boosting wins the headline metric
(MedAPE 10.54% against 10.78%) and the difference is not statistically distinguishable in
either direction.

Neither correction weakens the project. Together they make a better argument than the one
they replace: *three comparisons found no separation, so the choice had to be made on
grounds other than performance, and I will say what those grounds were rather than pretend
the data chose.* Those grounds are: gradient boosting ships inside scikit-learn, so
deploying it adds no dependency, and it won the metric named in advance.

---

## Before anything else

Three placeholders on the last slide need the real links once the app is deployed.
`.git` has no remote yet, so none of the three exists — if the defence comes first, say
"it runs locally, and I will show you" and delete the links slide rather than showing
empty boxes.

---

## Timing — 14 minutes, then questions

| Slides | Section | Minutes |
|---|---|---|
| 1 | Title, one-sentence pitch | 0:30 |
| 2–3 | Problem, data and cleaning | 2:00 |
| 4–6 | Three insights: logs, location, segments | 3:00 |
| 7–8 | **What the market pays for; the renovation correction** | 2:00 |
| 9–10 | **What it is worth; recommendations** | 2:00 |
| 11–13 | Model comparison, significance test, ratio study | 2:30 |
| 14–16 | Benchmark, where it is wrong, confidence by segment | 2:00 |
| 17 | **Live demo** | 1:30 |
| 18–20 | AI layer, limitations, close | 1:00 |

If you are running long, cut slide 6's classification paragraph to one sentence and shorten
slide 4. Do not cut slides 7, 8, 12 or 16 — the renovation correction, the significance
test and the segment bands are the four places where this project stops looking like a
tutorial.

---

## The demo, scripted — 90 seconds

1. The form is filled in. Press **Value this house**. *(5 s)*
2. "The model says $565,600. The number to work with is the range beside it — and note what
   it says underneath: that range is measured on houses in this segment, not on all houses.
   A premium property gets a range more than twice as wide." *(20 s)*
3. Point at the driver chart: "The zip code alone adds 21.6%. This is SHAP — a decomposition
   of *this* prediction, not a general claim about which features matter." *(20 s)*
4. Point at the explanation: "Written by a language model, and every number in it was
   checked against the evidence above before it was displayed." *(15 s)*
5. Open **Test it on real sales**: "These five are test-set houses, so the true sale price
   is known. This is the demo I cannot fake." *(20 s)*
6. "Five houses is a sample of five — the figure to quote is 10.5% across all 869." *(10 s)*

**If a five-house draw looks bad, that is the tab working.** Say the last line and move on.
Never hunt for a better seed in front of the room.

---

## The six questions from the roadmap

**"Why k = 4?"**
The elbow in inertia and the peak of the silhouette curve both pointed at four, and four
gave segments a person could name. Then add, before they do: the silhouette is 0.255, which
is weak — these are regions of a continuum, not four species of house. The segments earn
their place by being *useful* (the model's error differs sharply between them, and the app
now quotes a different confidence band for each), not by being cleanly separated.

**"Why did you delete 49 rows?"**
Every one had a price of zero or a living area of zero — impossible, not extreme. They were
1.1% of the file, and there is nothing to impute: imputing a price would be inventing the
target. Everything else was kept, including the $26m sale, because deleting hard houses
buys a flattering error rate and nothing else.

**"Why log-transform the price?"**
The error that matters is proportional — 10% on a $200k house and on a $2m house is the
same mistake; squared error on raw prices lets a handful of expensive houses dominate the
fit; and it makes the size–price relationship roughly linear. Skew falls from 4.02 to 0.34.
*On the back-transform:* `expm1` of a mean in log space predicts the median, not the mean.
Duan's smearing estimator made both bias and median error worse, so the notebook reports
the plain back-transform and says so.

**"Is 10–15% error good enough for a real business?"**
Not for a mortgage valuation — a lender needs an appraisal, and this model is eleven years
out of date. Yes for screening. Put it in money: half of all valuations land within
**$49,585** of the sale price; against the price-per-square-foot rule of thumb a broker
uses today the model cuts average error by **$18,683 a house**, and against a plain
zip-median lookup by **$73,098**. On 200 properties that is a different quality of decision
about where to send a valuer, for a minute of compute.

**"What would you do with more data?"**
Not more rows of the same ten weeks. In order of value: coordinates and building grade, so
location stops being a zip-code average — location is already 46% of the model on a coarse
proxy, so making the proxy finer is the cheapest improvement available; more months, so
seasonality and trend exist at all; then property tax records for a second opinion on value.

**"How do you know you have no data leakage?"**
Four defences, and the code for each:

1. `price_per_sqft` is on a hard exclusion list — it is price divided by size, so it
   contains the target. With it, R² is 0.99 and the model can only value houses already sold.
2. Every engineered feature is computed from a single row: no group means, no target.
3. Target encoding is the one place leakage could hide, so it lives inside the pipeline,
   fitted on training folds only, with out-of-fold encoding for the training rows — a row's
   own price never contributes to its own feature.
4. The split is fixed in `Data/split_indices.csv` and reused by every notebook; grid
   searches cross-validate *inside* the training set.

---

## The questions this version will attract

**"XGBoost looks better in your own table. Why did you ship the other one?"**
Because on the headline metric it is not better, and on the metric it wins the difference
is inside the noise: −0.41 percentage points with a 95% interval of [−1.25, +0.15] and
p = 0.84. Three comparisons found no separation. So I chose on grounds the test set cannot
settle: gradient boosting is in scikit-learn, so the deployed app needs no extra
dependency, and it won the metric I named before running anything. I would rather give an
engineering reason than dress up a coin-toss as a result.

**"Then what was the ratio study for?"**
It eliminated half the field. Ridge fails consistency and Random Forest fails vertical
equity — and vertical equity is a fairness property that R² and MAPE cannot see at all. It
narrowed four candidates to two. It did not, and I do not claim it did, pick between the
two survivors.

**"Why does the range change depending on the house?"**
Because the error does. Measured on the test set, the 10th-to-90th band is 38 points wide
for an Established Family Home and 82 points for a Premium View Property. One band for both
would be honest about neither. This came out of reviewing my own notebook — the app quoted
a single global band while my own diagnostics showed the error was segment-dependent — and
I fixed it rather than leaving it.

**"Is 'a bathroom is worth $40,432' a causal claim?"**
No, and it matters. It means homes with an extra bathroom sell for about that much more,
holding city and total floor area constant. It does not guarantee that *building* one
returns $40,432 — that needs renovation cost data, which this dataset does not contain.
The same caution is why the renovation slide gives a break-even rather than a return.

**"98.7% classification accuracy — is that leakage?"**
A fair suspicion, and no. The target is a k-means label, so the classifier only has to
reproduce a deterministic geometric rule; 98.7% measures how learnable that boundary is.
The real test is the blind experiment: a forest given only features k-means never saw still
recovers the segment about 82% of the time.

**"What is the single biggest weakness?"**
Ten weeks of 2014. Everything else — the top-decile bias, the Premium View segment, the
coarse location — is measured and fixable. That one is not fixable from this dataset, and
it means the model tells you what a house was worth in mid-2014, not today.

---

## Rehearsal, twice, out loud

**First run:** notes open, timing each section against the table. Expect to overrun; mark
where.

**Second run:** notes closed, recorded on your phone. Watch it with the sound on and look
for three things:

- **Filler** — "basically", "sort of". It arrives where you are unsure of the next sentence,
  so rehearse those transitions specifically.
- **Pace on the numbers.** 10.5%, $49,585, 3.2x, 1.030 — slowly enough to be written down.
  Everything else can move faster.
- **The demo.** Time it. It always takes longer than you think.

Then rehearse the opening thirty seconds separately, four or five times, until it is
automatic. The room decides how to listen to you in that half minute.

---

## Two things to remember on the day

**Your background is the advantage — use its vocabulary.** Credibility weighting, ratio
studies, vertical equity, a range rather than a point estimate, break-even rather than
return. These are actuarial instincts, and they are why this reads as a valuation exercise
rather than a Kaggle entry. When you explain the target encoder, say "credibility
weighting, the same Z = n/(n+k) used against thin cells in ratemaking" and the room will
hear where the choice came from.

**"I did not test that — here is how I would" is a strong answer.** You have measured a
great deal of this model. Be precise about the edge of what you measured, and the honesty
will read as confidence, because it is.
