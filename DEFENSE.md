# Day 14 — Presentation, rehearsal, and the questions

The deck is `reports/Real_Estate_Machine_defense.pptx` (18 slides, speaker notes on every
one). This file is the part the deck cannot carry: the timing, the demo script, and the
answers to the questions you will actually be asked.

---

## Before anything else

Three placeholders on the last slide must be replaced with the real links from Day 13:
the live app URL, the GitHub URL, and the Kaggle URL. The deck is otherwise finished.

---

## Timing — 14 minutes of talking, then questions

| Slides | Section | Minutes |
|---|---|---|
| 1 | Title, one-sentence pitch | 0:30 |
| 2–4 | Problem, data, cleaning decisions | 2:30 |
| 5–7 | Three insights: skew, location, segments | 3:00 |
| 8 | **Business recommendations** — slow down here | 1:30 |
| 9 | Classification, with the caveat | 1:00 |
| 10–12 | Model comparison, significance test, IAAO tie-break | 3:00 |
| 13–14 | Benchmark, and where it is wrong | 1:30 |
| 15 | **Live demo** | 1:30 |
| 16–18 | AI layer, limitations, links | 1:30 |

Slides 10–12 are the heart of the project. If you are running long, cut **slide 9** to two
sentences and shorten slide 3 — do not cut the significance test or the IAAO slide, because
they are what separate this from a leaderboard exercise.

---

## The demo, scripted — 90 seconds, in this order

1. The form is already filled in. Press **Value this house**. *(5 s)*
2. "The model says $565,600. But the number to work with is the range beside it —
   eight houses in ten land between $447,000 and $708,000." *(15 s)*
3. Point at the driver chart: "The zip code alone adds 21.5%. This is SHAP, computed from
   the model, not a general statement about which features matter — it is a decomposition
   of *this* prediction." *(20 s)*
4. Point at the explanation: "That paragraph is written by a language model, and every
   number in it was checked against the evidence above before it was displayed." *(15 s)*
5. Open **Test it on real sales**: "These five are test-set houses, so the true sale price
   is known. This is the demo I cannot fake." *(25 s)*
6. Close: "Five houses is a sample of five — the figure to quote is 10.5% across all 869."
   *(10 s)*

**If a five-house draw looks bad, that is the tab working, not failing.** Say the last line
and move on. Do not reach for a different seed in front of the room; it looks like you are
hunting for a flattering sample, because you would be.

**If the WiFi dies:** play the recording. If the laptop is dead too, slide 15 has the
screenshot and you can talk through it. Neither is an emergency.

---

## The six questions from the roadmap, answered

**"Why k = 4?"**
The elbow in inertia and the peak of the silhouette curve both pointed at four, and four
gave segments a person could name. Add, before they do: the silhouette is 0.255, which is
weak — these are regions of a continuum, not four species of house. The segments earn their
place by being *useful* (error differs sharply between them), not by being sharply separated.

**"Why did you delete 49 rows?"**
Every one had a price of zero or a living area of zero. That is not a cheap house, it is
missing data wearing a number. They were 1.1% of the file, and there is nothing to impute —
imputing a price would be inventing the target. Everything else was kept, including the
$26m sale, because deleting expensive houses to flatter the error rate is how a model
becomes useless.

**"Why log-transform the price?"**
Three reasons, in order: the error that matters is proportional, not absolute — 10% on a
$200k house and 10% on a $2m house are the same mistake; squared error on raw prices lets a
handful of expensive houses dominate the fit; and it makes the size–price relationship
roughly linear. Skew falls from 4.02 to 0.34.
*If pressed on the back-transform:* `expm1` of a mean in log space predicts the median, not
the mean. I tested Duan's smearing estimator to correct that and it made both the bias and
the median error worse, so I report the plain back-transform and say so in the notebook.

**"Is 10–15% error good enough for a real business?"**
Not for a mortgage valuation — a lender needs an appraisal, and the model is 11 years out of
date. Yes for screening: a broker can run 200 listings in a minute, get a range and a
confidence flag for each, and send a valuer only to the ones the model is least sure about.
The honest framing is that the product is speed plus an honest confidence statement, not
accuracy. For scale: Zillow's off-market Zestimate is around 7.5% on far richer data;
48% of my valuations land within 10% of the sale price.

**"What would you do with more data?"**
Not more rows of the same ten weeks — those are nearly exhausted. In order of value:
more *time*, so seasonality and market trend become visible and the model is not frozen in
mid-2014; coordinates, so location becomes distance-to-water, distance-to-station,
school catchment, instead of a zip-code average; building grade and lot topography; and
property tax records for a second opinion on value.

**"How do you know you have no data leakage?"**
Four specific defences, and I can point at the code for each:

1. `price_per_sqft` is on a hard exclusion list. It is price divided by size, so it contains
   the target. With it, R² is about 0.99 and the model can only value houses already sold.
2. Every engineered feature is computed from a single row. Nothing uses a group mean, and
   nothing looks at the target — so it is safe to compute before the split.
3. Target encoding is the one place leakage could hide, so it lives inside the pipeline and
   is fitted on training folds only, with out-of-fold encoding for the training rows
   themselves: a row's own price never contributes to its own feature.
4. The train/test split is fixed in `Data/split_indices.csv` and reused by every notebook,
   so no model has ever been tuned against the rows it is scored on. Grid searches
   cross-validate *within* the training set.

---

## Five more they are likely to ask

**"98.7% classification accuracy — is that leakage?"**
No, and it is a fair suspicion. The target is a k-means label, so the classifier only has to
reproduce a deterministic geometric rule; 98.7% measures how learnable that boundary is, not
how well I understand houses. The real test is the blind experiment: a forest given only
features k-means never saw still recovers the segment about 82% of the time, so the segments
carry information beyond their own definition.

**"Why gradient boosting rather than XGBoost — it was nearly the same?"**
Because on the accuracy metric they are *not distinguishable*: the difference was 0.18
percentage points with a bootstrap CI of [−0.72, +0.49] and p = 0.20. Calling that a win
would be dishonest. The tie-break was the IAAO ratio study, where the gradient booster is
the only one of the four models that passes median ratio, COD and PRD together.

**"What is PRD and why do you care?"**
Price-related differential — the mean ratio divided by the sales-weighted mean ratio. It
detects a model that over-values cheap homes and under-values expensive ones. In an
assessment context that means poorer owners subsidise wealthier ones, and it is invisible in
R² or in MAPE. Mine is 1.030, at the edge of the 0.98–1.03 band, and I know exactly why:
trees cannot extrapolate above the training range, so the top decile is under-valued.

**"Is the AI making up the valuation?"**
No. The model predicts, SHAP decomposes, deterministic rules raise the warnings, and only
then does a language model write sentences from that finished evidence. Every number it
writes is parsed back out and rejected if it is not in the evidence. There is a tick-box in
the app that turns it off — the valuation, the range, the drivers and the warnings are
identical with it off.

**"What is the single biggest weakness?"**
The data is ten weeks of 2014. Everything else — the top-decile bias, the Premium View
segment, the coarse location — is measurable and fixable. That one is not fixable from this
dataset, and it means the model tells you what a house was worth in mid-2014, not today.

---

## Rehearsal, twice, out loud

**First run:** with the notes open, timing each section against the table above. Expect to
overrun; note where.

**Second run:** notes closed, recorded on your phone. Then watch it, with the sound on, and
look for three specific things:

- **Filler.** "Basically", "sort of", "kind of" — they arrive when you are unsure of the
  next sentence, so mark where they cluster and rehearse only those transitions.
- **Pace on the numbers.** 10.5%, 869 houses, 1.030 — say each one slowly enough that
  someone can write it down. Everything else can move faster.
- **The demo.** Time it. It always takes longer than you think, and it is the part where you
  will be tempted to improvise.

Then rehearse the *opening thirty seconds* separately, three or four times, until it is
automatic. The room decides how to listen to you in that half-minute, and it is the moment
you will be most nervous.

---

## Two things worth remembering on the day

**Your background is an advantage — use the vocabulary.** Credibility weighting, ratio
studies, vertical equity, an honest range rather than a point estimate: these are actuarial
instincts, and they are why this project looks like a valuation exercise rather than a
Kaggle entry. Say "credibility weighting, the same `Z = n/(n+k)` used against thin cells in
ratemaking" when you explain the target encoder, and the room will hear that the choice came
from somewhere.

**"I did not test that — here is how I would" is a strong answer.** It is much stronger than
a confident guess, and examiners can tell the difference instantly. You have measured a great
deal of this model; be precise about the edge of what you measured.
