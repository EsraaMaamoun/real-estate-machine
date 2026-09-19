# Ink & Amber — the project's visual identity

One system, three places: the slide deck, the charts, and the live app. The point is
that an examiner watching you switch from the deck to the demo should not feel the
switch.

---

## Why the app looked wrong before

Streamlit follows the viewer's operating system unless you tell it not to, which is
why your screenshots came out dark with a red accent while the deck was light and
warm. `.streamlit/config.toml` now pins the theme, so the app looks the same on your
laptop, on the projector, and on Streamlit Community Cloud.

That file must be committed to the repository — the deployed app reads it on start-up.
`.gitignore` excludes `.streamlit/secrets.toml` (your key) but not `config.toml`.

---

## The tokens

| Role | Colour | Where |
|---|---|---|
| Paper | `#FBFAF7` | slide and app background |
| Card | `#F2EFE9` | a block of related content |
| Warm card | `#FAF0E2` | a card making the point of the slide |
| Ink | `#191714` | headlines, dark slides |
| Body | `#3A342C` | body text |
| Muted | `#6B6358` | captions, axis labels |
| **Amber** | `#C07214` | **the subject**: this model, this house, the answer |
| **Teal** | `#0094A0` | **a gain, a pass** |
| **Brick** | `#B23A20` | **a loss, a failure** |
| Graphite / Stone | `#4A4640` / `#C9C2B6` | neutral context — the bars a highlighted bar is compared against |

Only amber, teal and brick are allowed to carry meaning. Everything else is context.
That rule is what stops a chart from looking decorated.

**The three meaning colours were checked, not chosen by eye.** Against the paper
surface they pass the lightness band, the chroma floor, colour-blind separation
(worst adjacent pair ΔE 16.5 under protanopia, against a floor of 8), the
normal-vision floor and 3:1 contrast. A second set was validated for the dark slides.
If an examiner asks why those colours: that is the answer.

**Type:** Cambria for headlines, Calibri for everything else. Both ship with Office,
so the deck renders identically on the examiner's machine.

**The one repeated mark:** an amber eyebrow label above every slide title, and an
amber band down the left edge of the three dark slides. No underlines beneath
titles, no decorative bars — they are the giveaway of a generated deck.

---

## The files

| File | What it holds |
|---|---|
| `scripts/design.py` | the tokens, and the matplotlib defaults every chart inherits |
| `.streamlit/config.toml` | the same tokens for the app |
| `app/charts.py` | the driver chart, using the teal/brick diverging pair |
| `app/app.py` | a small CSS block: serif headings, amber eyebrow and rule |
| `scripts/make_slide_figs.py` | the three model figures |
| `scripts/make_business_figs.py` | the seven business figures |
| `scripts/build_deck.js` | the deck |

To change a colour everywhere, change it in `scripts/design.py` and
`.streamlit/config.toml`, then re-run the two figure scripts and `build_deck.js`.

---

## The live URL and the QR code

The closing slide is built for two states and needs no hand editing.

**Now** (nothing deployed): three labelled slots reading *to be added once deployed*,
and a dashed amber frame where the QR will go.

**Once the app is live:**

```bash
python scripts/make_qr.py https://your-app.streamlit.app \
    --repo https://github.com/<you>/real-estate-machine \
    --kaggle https://www.kaggle.com/code/<you>/real-estate-machine
node scripts/build_deck.js
```

The first command writes `reports/slides/qr_live_app.png` and records the URLs in
`deck_facts.json`; the second rebuilds the deck with the real code and the real links
in place of the placeholders. The QR is drawn in ink on paper at the highest error
correction level, so it still scans from a projector at an angle.

Leave that slide up during questions — anyone in the room can open the tool on their
own phone while you answer.

---

## If you present before deploying

Say "it runs locally, and I have just shown you," and move on. Do not apologise for
the empty slots; a placeholder that looks deliberate reads as a plan, and this one
does.
