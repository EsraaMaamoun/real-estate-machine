"""
app.py — EstateIQ, the product interface of the Real Estate Machine project.

EstateIQ is the name the user sees; `real-estate-machine` stays the repository name, so
the deployed URL and every existing link keep working.

What this file is, and what it is deliberately NOT
--------------------------------------------------
This is the front door of the project: a form, a valuation, and an explanation.

It contains **no modelling logic of its own**. Not one threshold, not one derived
feature, not one rule about what counts as a large house. Every number shown on
screen is computed by `explain.py`, which loads the trained model and calls
the same `preprocessing.py` the model was trained with.

That is the single most important design decision in the whole app, and it is the
question an examiner is most likely to ask: *how do you know the app preprocesses a
house exactly the way training did?* The answer is that it cannot do otherwise —
there is only one copy of the code, imported by both.

    training  preprocessing.py  ->  trained the model      ->  Models/regressor.pkl
    serving   preprocessing.py  ->  values this house      ->  same transformations

Layout
------
    Tab 1  Value a house      the demo
    Tab 2  Test on real sales five rows with a known sale price, so the demo is falsifiable
    Tab 3  About the model    the honest performance and limitations page

Run it
------
    streamlit run app/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------
# Imports from our own modules.
#
# Streamlit runs this file as a script, so `app/` is on sys.path already when you
# launch with `streamlit run app/app.py`. It is NOT on the path if the app is
# launched from somewhere else (Streamlit Community Cloud does this), so add it
# explicitly rather than relying on the working directory.
# --------------------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent
sys.path.insert(0, str(APP_DIR))

from explain import HouseValuer, REQUIRED_FIELDS  # noqa: E402
from charts import driver_chart  # noqa: E402
import llm_explain  # noqa: E402


def _load_secrets_into_env() -> None:
    """Bridge Streamlit Cloud's secrets into the environment.

    Locally the API key comes from `.env`, which `llm_explain` reads with
    python-dotenv. There is no `.env` on Streamlit Community Cloud - the key is
    pasted into the app's Secrets box instead, and reaches the app as `st.secrets`.

    Copying those secrets into `os.environ` here means `llm_explain` needs no cloud
    branch at all: it keeps reading `os.getenv`, and behaves identically in both
    places. Wrapped in try/except because `st.secrets` raises rather than returning
    empty when there is no secrets file, which is the normal local case.
    """
    import os

    try:
        for key in ("GEMINI_API_KEY", "GROQ_API_KEY", "GEMINI_MODEL", "GROQ_MODEL"):
            if key in st.secrets and not os.getenv(key):
                os.environ[key] = str(st.secrets[key])
    except Exception:
        pass


_load_secrets_into_env()

MODELS = ROOT / "Models"
DATA = ROOT / "Data"

st.set_page_config(page_title="EstateIQ", layout="wide")


# --------------------------------------------------------------------------
# Loading — done once per session, not once per keystroke
# --------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading the model...")
def load_valuer() -> HouseValuer:
    """Load the model, the segmenter and the reference statistics exactly once.

    `@st.cache_resource` is the right decorator here (not `@st.cache_data`): the
    valuer is a live object holding an unpickled model, not a value to be copied.
    Streamlit re-runs this whole script top to bottom on every widget change, so
    without this decorator the app would unpickle a gradient booster every time
    you moved a slider.
    """
    return HouseValuer(MODELS)


@st.cache_resource(show_spinner=False)
def load_explainer(_valuer: HouseValuer):
    """Force the lazy SHAP explainer to build once, up front.

    Building a TreeExplainer costs about a second. Doing it here means the first
    valuation is not the one that pays for it, which matters when the first
    valuation is the one happening in front of an examiner.
    """
    try:
        # Assigned, not left bare: Streamlit's "magic" renders a bare expression, and a
        # bare `_valuer.explainer` would dump the whole TreeExplainer repr onto the page.
        _ = _valuer.explainer
        return True
    except Exception:
        return False


@st.cache_data(show_spinner=False)
def load_sales() -> pd.DataFrame | None:
    """The cleaned dataset, used only by the 'Test on real sales' tab."""
    path = DATA / "data_clean.csv"
    if not path.exists():
        return None
    return pd.read_csv(path, dtype={"zipcode": str})


def money(x: float) -> str:
    return f"${x:,.0f}"


# --------------------------------------------------------------------------
# Startup checks — fail loudly and usefully, never silently
# --------------------------------------------------------------------------
missing = [f for f in ["regressor.pkl", "regressor_config.pkl"] if not (MODELS / f).exists()]
if missing:
    st.error(
        "The app cannot start because these model files are missing from `Models/`: "
        + ", ".join(f"`{m}`" for m in missing)
        + ".\n\nRun `Notebooks/09_model_tuning.ipynb` (which saves the regressor) and "
        "`Notebooks/10_llm_explanation.ipynb` (which saves `reference_stats.pkl`) first."
    )
    st.stop()

valuer = load_valuer()
has_shap = load_explainer(valuer)
cfg = valuer.config
ref = valuer.ref

known_zips = sorted(ref.get("known_zipcodes", []))
known_cities = sorted(ref.get("known_cities", []))


# --------------------------------------------------------------------------
# Identity
#
# `.streamlit/config.toml` carries the colours; this carries the typography and
# the two details that make the app and the slide deck read as one product: a
# serif headline and an amber rule, here under the EstateIQ name and tagline.
#
# Deliberately small. Streamlit renames its internal CSS classes between
# versions, so anything that targets them breaks on upgrade; everything below
# targets plain HTML elements or documented test ids, and the app is perfectly
# usable if a rule silently stops applying.
# --------------------------------------------------------------------------
BRAND_CSS = """
<style>
  h1, h2, h3 { font-family: Cambria, Georgia, "Times New Roman", serif !important;
               letter-spacing: -0.01em; }
  h1 { font-size: 2.5rem !important; margin-bottom: 0.1rem !important; }
  [data-testid="stMetricValue"] {
      font-family: Cambria, Georgia, serif !important; font-weight: 700; }
  [data-testid="stMetricLabel"] { color: #6B6358 !important; }
  .rem-tagline { font-size: 1.05rem; color: #6B6358; margin-top: 0.15rem; }
  .rem-rule { height: 3px; width: 64px; background: #C07214; margin: 0.55rem 0 0.9rem 0; }
  div[data-testid="stAlert"] { border-radius: 8px; }

  /* The product disclaimer: the first thing read after the name, on purpose. */
  .rem-disclaimer { background: #F2EFE9; border-left: 4px solid #C07214;
                    border-radius: 6px; padding: 0.6rem 0.95rem; margin: 0.35rem 0 1.1rem 0;
                    font-weight: 600; color: #191714; }

  /* The valuation hierarchy: one hero number, then everything that qualifies it. */
  .rem-label { font-size: 0.875rem; color: #6B6358; margin-bottom: 0.05rem; }
  .rem-value { font-family: Cambria, Georgia, serif; font-weight: 700; font-size: 3.2rem;
               line-height: 1.05; color: #191714; margin-bottom: 0.7rem; }

  /* A quiet but explicit note, used for what the language model does and does not do. */
  .rem-note { border-left: 2px solid #C07214; padding: 0.1rem 0 0.1rem 0.75rem;
              margin: 0 0 0.85rem 0; color: #6B6358; font-size: 0.93rem; }
</style>
"""
st.markdown(BRAND_CSS, unsafe_allow_html=True)

st.title("EstateIQ")
st.markdown(
    '<div class="rem-tagline">AI-Assisted Real Estate Valuation &amp; Decision Support</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="rem-rule"></div>', unsafe_allow_html=True)

# The model's name and hyperparameters live under "Technical details" on the About tab;
# the header says only what a user needs: what it learned from and how wrong it runs.
_n_train = cfg.get("n_train")
st.caption(
    (f"Trained on {_n_train:,} Washington State home sales (May–July 2014). "
     if _n_train else "Trained on Washington State home sales (May–July 2014). ")
    + f"Typical error on homes it had never seen: {cfg['test_MedAPE_%']:.1f}% (median)."
)
st.markdown(
    '<div class="rem-disclaimer">Decision-support tool — not a formal property appraisal.</div>',
    unsafe_allow_html=True,
)

tab_value, tab_test, tab_about = st.tabs(
    ["Value a house", "Test it on real sales", "About the model"]
)


# --------------------------------------------------------------------------
# Tab 1 — the demo
# --------------------------------------------------------------------------
def show_evidence(evidence: dict, actual_price: float | None = None):
    """Render one dossier in the order a reader needs it.

        Estimated value -> range -> market segment -> what moved it -> warnings

    The AI-assisted explanation comes last and is rendered by the caller, because it is
    the only step that may make a network call - and the only one that must never be
    mistaken for the source of the number.
    """
    # 1. Estimated value - one number, on its own line, the largest thing on the page.
    #    "&#36;" rather than "$": this goes through st.markdown, where a stray pair of
    #    dollar signs is read as LaTeX.
    st.markdown(
        '<div class="rem-label">Estimated value</div>'
        f'<div class="rem-value">{money(evidence["predicted_price"]).replace("$", "&#36;")}</div>',
        unsafe_allow_html=True,
    )

    # 2. The range, and what qualifies it.
    c1, c2 = st.columns([1.5, 1])
    # No "$" inside this value: Streamlit renders metric text as markdown, and two dollar
    # signs in one string are read as LaTeX. The unit goes in the label instead.
    c1.metric("Estimated valuation range, $  (8 of 10 houses)",
              f"{evidence['range_low']:,.0f} - {evidence['range_high']:,.0f}")
    if actual_price is None:
        c2.metric("Implied price per sqft", money(evidence["price_per_sqft"]))
    else:
        err = 100 * abs(evidence["predicted_price"] - actual_price) / actual_price
        c2.metric("Actual sale price", money(actual_price), f"{err:.1f}% error",
                  delta_color="off")

    # Which houses that range was measured on. The band is segment-specific when
    # Models/segment_intervals.pkl is present, and saying so is the difference
    # between a range and a guess dressed as one.
    st.caption(
        f"The range is the 10th-to-90th percentile of this model's error on "
        f"{evidence.get('range_basis', 'all houses in the test set')} "
        f"({evidence.get('range_width_pp', 47)} percentage points wide)."
    )

    # 3. Market segment.
    if evidence.get("segment"):
        st.subheader("Market segment")
        line = f"**{evidence['segment']}**"
        if evidence.get("segment_typical_error_pct"):
            line += (f" — typical error for this segment: "
                     f"{evidence['segment_typical_error_pct']}%")
        st.markdown(line)

    # 4. What moved the valuation.
    st.subheader("What moved the valuation")
    if has_shap:
        st.pyplot(driver_chart(evidence["drivers"]))
        with st.expander("Technical details"):
            st.caption(
                "SHAP values, converted from log space to a percentage effect on the price. "
                "They add up to the difference between this house and the average house — "
                "this is a decomposition of the actual prediction, not a general statement "
                "about which features matter."
            )
    else:
        st.dataframe(
            pd.DataFrame(evidence["drivers"])[["label", "value", "pct_effect"]]  # pyright: ignore[reportCallIssue]
            .rename(columns={"label": "driver", "value": "this house",
                             "pct_effect": "effect on price (%)"}),
            hide_index=True,
        )

    # 5. Warnings - the heading is always shown, so "none" is a stated result,
    #    not an absence the reader has to notice.
    st.subheader("Warnings")
    if evidence["flags"]:
        for f in evidence["flags"]:
            st.warning(f)
    else:
        st.success("No warnings were triggered for this house.")


with tab_value:
    left, right = st.columns([1, 1.35], gap="large")

    with left:
        st.subheader("The house")
        with st.form("house"):
            a, b = st.columns(2)
            bedrooms = a.number_input("Bedrooms", 0, 15, 3, 1)
            bathrooms = b.number_input("Bathrooms", 0.0, 10.0, 2.0, 0.25)
            sqft_living = a.number_input("Living area (sqft)", 100, 15000, 1800, 50)
            sqft_lot = b.number_input("Lot size (sqft)", 100, 500000, 7500, 100)
            floors = a.number_input("Floors", 1.0, 4.0, 1.0, 0.5)
            sqft_basement = b.number_input("Basement area (sqft)", 0, 5000, 0, 50)
            yr_built = a.number_input("Year built", 1850, 2014, 1985, 1)
            yr_renovated = b.number_input(
                "Year renovated (0 if never)", 0, 2014, 0, 1)
            condition = a.slider("Condition", 1, 5, 3,
                                 help="1 = poor, 5 = excellent")
            view = b.slider("View rating", 0, 4, 0,
                            help="0 = no view, 4 = exceptional")
            waterfront = a.selectbox("Waterfront", [0, 1],
                                     format_func=lambda v: "Yes" if v else "No")

            city = st.selectbox(
                "City", known_cities or ["Seattle"],
                index=(known_cities.index("Seattle") if "Seattle" in known_cities else 0),
            )
            zipcode = st.selectbox(
                "Zip code", known_zips or ["98115"],
                index=(known_zips.index("98115") if "98115" in known_zips else 0),
            )

            use_llm = st.checkbox(
                "Write an AI-assisted explanation", value=True,
                help="Unticked, the app writes the same explanation deterministically "
                     "from the same evidence. Nothing about the valuation changes.",
            )
            submitted = st.form_submit_button("Value this house", type="primary")

        st.caption(
            "City and zip code are limited to the ones the model saw in training. "
            "Typing an unknown location would not fail — it would quietly fall back to "
            "the market average, which is the largest driver in the model. A drop-down "
            "makes that impossible rather than merely warned about."
        )

    with right:
        if not submitted:
            st.info(
                "Fill in the house on the left and press **Value this house**.\n\n"
                "The estimated value, its range, the market segment, what moved the "
                "valuation, any warnings and an AI-assisted explanation will appear here."
            )
        else:
            house = {
                "bedrooms": int(bedrooms), "bathrooms": float(bathrooms),
                "sqft_living": int(sqft_living), "sqft_lot": int(sqft_lot),
                "floors": float(floors), "waterfront": int(waterfront),
                "view": int(view), "condition": int(condition),
                "sqft_basement": int(sqft_basement), "yr_built": int(yr_built),
                "yr_renovated": (int(yr_renovated) or None),
                "city": city, "zipcode": str(zipcode),
            }

            problems = HouseValuer.validate(house)
            if problems:
                # A refusal, not a guess. See explain.HouseValuer.validate.
                st.error("This house cannot be valued:\n\n"
                         + "\n".join(f"- {p}" for p in problems))
            else:
                evidence = valuer.evidence(house)
                show_evidence(evidence)

                # 6. The explanation - produced after the evidence, never before it.
                if use_llm:
                    with st.spinner("Writing the explanation..."):
                        out = llm_explain.explain_prediction(evidence)
                else:
                    out = {"text": llm_explain.fallback_explanation(evidence),
                           "source": "deterministic", "grounded": True,
                           "ungrounded_numbers": [], "error": None}

                source = out["source"]
                # Only call it AI-assisted when a language model actually wrote it. The
                # cache holds language-model text too; the deterministic template and the
                # fallback do not, and labelling them "AI" would be a small lie.
                ai_written = source in ("gemini", "groq", "cache")
                if ai_written:
                    st.subheader("AI-assisted explanation")
                    st.markdown(
                        '<div class="rem-note">The language model explains evidence produced '
                        'by the valuation model; it does not determine the valuation.</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.subheader("Explanation")

                # Escape the dollar signs before rendering. Streamlit renders markdown,
                # and a pair of unescaped "$" in the same paragraph is read as LaTeX -
                # which silently swallows "$565,600 ... $314" into a maths block.
                st.write(out["text"].replace("$", r"\$"))

                if source in ("gemini", "groq"):
                    st.caption(
                        f"Written by {source}. Every number in that paragraph was "
                        "checked against the evidence above before it was shown to you."
                    )
                elif source == "cache":
                    st.caption("Served from the local cache: this exact valuation was "
                               "explained before, and every number was re-checked against "
                               "the evidence above. No network call was made.")
                elif source == "deterministic":
                    st.caption("Written in Python from the evidence above. No model call.")
                else:
                    st.caption(
                        f"Written in Python from the evidence above, because the language "
                        f"model was not used: {out['error']}."
                    )
                    if out.get("ungrounded_numbers"):
                        st.error(
                            "The language model's answer was rejected: it contained "
                            f"{out['ungrounded_numbers']}, which are not in the evidence. "
                            "The deterministic explanation is shown instead."
                        )


# --------------------------------------------------------------------------
# Tab 2 — the demo you cannot fake
# --------------------------------------------------------------------------
with tab_test:
    st.subheader("Five real sales, and what the model would have said")
    st.markdown(
        "These properties come from the held-out test set and were not seen during "
        "training. Their sale prices are known, so every estimate below can be checked "
        "against what the house actually sold for."
    )

    sales = load_sales()
    split_path = DATA / "split_indices.csv"

    if sales is None or not split_path.exists():
        st.info("`Data/data_clean.csv` and `Data/split_indices.csv` are needed for this "
                "tab and are not present in this deployment.")
    else:
        split = pd.read_csv(split_path, index_col="row")["split"]
        test_rows = sales[split.values == "test"].reset_index(drop=True)

        seed = st.number_input("Sample seed", 0, 9999, 42, 1,
                               help="Change it to draw a different five houses. "
                                    "Every draw comes from the test set.")
        picks = test_rows.sample(5, random_state=int(seed))

        rows = []
        for _, r in picks.iterrows():
            # r is a Series from iterrows(), so pandas-stubs cannot narrow r["x"] to a
            # scalar; at runtime every field here is one, so the int()/float() calls
            # below are correct despite the wide static type pyright infers for r[...].
            house = {
                "bedrooms": int(r["bedrooms"]), "bathrooms": float(r["bathrooms"]),  # pyright: ignore[reportArgumentType]
                "sqft_living": int(r["sqft_living"]), "sqft_lot": int(r["sqft_lot"]),  # pyright: ignore[reportArgumentType]
                "floors": float(r["floors"]), "waterfront": int(r["waterfront"]),  # pyright: ignore[reportArgumentType]
                "view": int(r["view"]), "condition": int(r["condition"]),  # pyright: ignore[reportArgumentType]
                "sqft_basement": int(r["sqft_basement"]), "yr_built": int(r["yr_built"]),  # pyright: ignore[reportArgumentType]
                "yr_renovated": (int(r["yr_renovated"])  # pyright: ignore[reportArgumentType]
                                 if pd.notna(r.get("yr_renovated")) and r["yr_renovated"] > 0  # pyright: ignore[reportGeneralTypeIssues]
                                 else None),
                "city": str(r["city"]), "zipcode": str(r["zipcode"]),
            }
            try:
                ev = valuer.evidence(house, top_k=3)
            except ValueError as exc:
                rows.append({"house": "refused", "why": str(exc)})
                continue
            actual = float(r["price"])  # pyright: ignore[reportArgumentType]
            rows.append({
                "city": house["city"],
                "zip": house["zipcode"],
                "beds": house["bedrooms"],
                "sqft": house["sqft_living"],
                "actual sale": actual,
                "estimated value": ev["predicted_price"],
                "error %": 100 * (ev["predicted_price"] - actual) / actual,
                "segment": ev["segment"],
            })

        table = pd.DataFrame(rows)
        st.dataframe(
            table.style.format({"actual sale": "${:,.0f}", "estimated value": "${:,.0f}",
                                "error %": "{:+.1f}%", "sqft": "{:,.0f}"}),
            hide_index=True,
        )

        med = table["error %"].abs().median()
        st.markdown(
            f"Median absolute error on these five: **{med:.1f}%**, against "
            f"**{cfg['test_MedAPE_%']:.1f}%** across the whole test set of "
            f"{len(test_rows):,} houses. Five houses is far too small a sample to "
            "judge a model on — change the seed and this number moves several points. "
            "The test-set figure is the one to quote."
        )


# --------------------------------------------------------------------------
# Tab 3 — the honesty page
# --------------------------------------------------------------------------
with tab_about:
    st.subheader("How well it actually works")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Typical error (median)", f"{cfg['test_MedAPE_%']:.1f}%")
    m2.metric("Mean error", f"{cfg['test_MAPE_%']:.1f}%")
    m3.metric("Within 10% of sale price", f"{cfg['test_PPE10_%']:.0f}%")
    m4.metric("R2 (log price)", f"{cfg['test_R2_log']:.3f}")

    st.markdown(
        "Selected from four candidate models after tuning and validation on sales it "
        "never saw, and checked against the ratio-study standards property assessors "
        "use. The model comparison, the statistical tests and the full methodology are "
        "under **Technical details** at the bottom of this page."
    )

    st.subheader("Where it is weak — say this before anyone asks")
    for w in cfg.get("known_weaknesses", []):
        st.markdown(f"- {w}")
    st.markdown(
        """
- Only ten weeks of 2014 data: no seasonality, no market trend, and the price level is
  eleven years out of date.
- Washington State only. It will not generalise to another market.
- No building grade and no coordinates, so location is captured coarsely by zip code.
- About 33 waterfront homes in the whole dataset — too few to be confident about any of them.
"""
    )

    if cfg.get("segment_MedAPE"):
        st.subheader("Typical error by market segment")
        seg = (pd.Series(cfg["segment_MedAPE"]).sort_values()
               .rename("median error %").to_frame())
        st.dataframe(seg.style.format({"median error %": "{:.1f}%"}))

    # Everything below is unchanged in substance - moved, not removed. A reviewer who
    # wants the hyperparameters, the significance test or the IAAO figures opens one
    # section; a user who does not is not made to scroll past them.
    with st.expander("Technical details"):
        st.markdown(
            f"""
**Model and hyperparameters.** {cfg['model_name']} — `{cfg.get('sklearn_params', {})}` —
predicting `{cfg['target']}` and back-transformed with `{cfg['back_transform']}`.

**Model comparison and statistical test.** Chosen over Ridge, Random Forest and XGBoost.
It beat Ridge by about 2 percentage points of median error, a difference that survived a
paired significance test. It did **not** beat XGBoost by a distinguishable margin; the
tie was broken on the IAAO ratio study below, which XGBoost fails.

**The IAAO ratio study.** The assessment industry judges a valuation model on three
statistics rather than on accuracy alone:
median ratio **{cfg['iaao']['median_ratio']:.3f}** (target 0.90-1.10, no systematic
over- or under-valuation), COD **{cfg['iaao']['cod']:.2f}** (target 5-15, consistency),
PRD **{cfg['iaao']['prd']:.3f}** (target 0.98-1.03, cheap and expensive homes treated
alike). This model passes all three. It is the only one of the four that does.

**How a valuation is produced.**
"""
        )
        st.code(
            "your inputs\n"
            "  -> preprocessing.engineer_features()   the same function that built the training set\n"
            "  -> the fitted pipeline                 scaling + smoothed target encoding, fitted on TRAIN only\n"
            "  -> " + cfg["model_name"] + "\n"
            "  -> np.expm1()                          back to dollars\n"
            "  -> SHAP                                what moved this particular prediction\n"
            "  -> deterministic checks                the warnings\n"
            "  -> language model                      turns all of the above into sentences\n"
            "  -> grounding check                     rejects any number it was not given",
            language="text",
        )
        st.caption(
            "The language model is the last step and the least important one. It cannot "
            "change a valuation; it can only describe one, and every figure it writes is "
            "verified against the evidence before you see it."
        )
