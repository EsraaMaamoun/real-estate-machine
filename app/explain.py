"""
explain.py — the evidence layer.

Why this exists
---------------
Day 11 adds a language model that writes a paragraph about a valuation. A language
model given no evidence invents evidence. So before any prompt is built, this module
turns one house into a small, fully-computed dossier:

    the prediction, an honest range around it, the market segment, the top drivers
    from SHAP, and a list of deterministic warnings

Every number in that dossier is computed here, in Python, from the model saved on
Day 10. The language model is never asked to work anything out — it is only asked to
put these numbers into sentences. That separation is the whole design, and it is what
makes the AI layer defensible rather than decorative.

This module is also what the Day 12 Streamlit app calls. The app must never re-derive
a feature or a threshold of its own.

Usage
-----
    from explain import HouseValuer

    valuer = HouseValuer()                 # loads Models/regressor.pkl etc.
    evidence = valuer.evidence({
        "bedrooms": 3, "bathrooms": 2.0, "sqft_living": 1800, "sqft_lot": 7500,
        "floors": 1.0, "waterfront": 0, "view": 0, "condition": 3,
        "sqft_basement": 500, "yr_built": 1985, "yr_renovated": None,
        "city": "Seattle", "zipcode": "98115",
    })
    evidence["predicted_price"], evidence["drivers"], evidence["flags"]
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

import preprocessing as P

DEFAULT_MODELS_DIR = Path(__file__).resolve().parent.parent / "Models"

# Fields the user has to supply. sqft_above is derived, not asked for.
REQUIRED_FIELDS = [
    "bedrooms", "bathrooms", "sqft_living", "sqft_lot", "floors",
    "waterfront", "view", "condition", "sqft_basement",
    "yr_built", "city", "zipcode",
]

# Day 6 kept both a raw and a logged version of the two area columns, so the model
# splits the size effect between them. SHAP is additive, so the honest way to show
# that to a human is to add the two contributions back together and report one
# "living area" figure instead of two half-figures that look like separate reasons.
MERGE_INTO = {"log_sqft_living": "sqft_living", "log_sqft_lot": "sqft_lot"}

# Plain-English names, so neither the app nor the prompt shows a column name.
READABLE = {
    "zipcode_te": "the zip code",
    "city_te": "the city",
    "sqft_living": "living area",
    "log_sqft_living": "living area (log scale)",
    "sqft_lot": "lot size",
    "log_sqft_lot": "lot size (log scale)",
    "bedrooms": "bedrooms",
    "bathrooms": "bathrooms",
    "floors": "floors",
    "waterfront": "waterfront location",
    "view": "view rating",
    "condition": "condition rating",
    "sqft_basement": "basement area",
    "house_age": "age of the house",
    "was_renovated": "renovation history",
    "years_since_reno": "years since it was last renewed",
    "has_basement": "having a basement",
    "basement_ratio": "share of the space that is below grade",
    "bath_per_bed": "bathrooms per bedroom",
    "sqft_per_room": "space per room",
}


class HouseValuer:
    """Loads the Day 10 artifacts once and values single houses."""

    def __init__(self, models_dir: str | Path | None = None):
        self.models_dir = Path(models_dir or DEFAULT_MODELS_DIR)

        self.model = joblib.load(self.models_dir / "regressor.pkl")
        self.config = joblib.load(self.models_dir / "regressor_config.pkl")
        self.features = self.config["features"]
        self.output_order = self.config["output_order"]
        self.lo_pct, self.hi_pct = self.config["interval_pct_10_90"]

        # Optional: the Day 7 segmenter. Absent is fine, the evidence just omits it.
        self.cluster_pipe = self._maybe("cluster_pipeline.pkl")
        self.cluster_cfg = self._maybe("cluster_config.pkl")

        # Optional: training-set reference statistics, written by Notebook 10.
        self.ref = self._maybe("reference_stats.pkl") or {}

        self._explainer = None  # SHAP is built lazily; it costs a second

    # -- loading helpers ---------------------------------------------------
    def _maybe(self, filename):
        path = self.models_dir / filename
        return joblib.load(path) if path.exists() else None

    @property
    def explainer(self):
        if self._explainer is None:
            import shap  # imported here so the app still runs without SHAP installed
            self._explainer = shap.TreeExplainer(self.model.named_steps["model"])
        return self._explainer

    # -- input handling ----------------------------------------------------
    @staticmethod
    def validate(house: dict) -> list[str]:
        """Return a list of problems. Empty list means the input is usable.

        These are hard errors, not warnings: a house with zero square feet is not an
        unusual house, it is a typing mistake, and the model should refuse rather than
        return a confident number for it.
        """
        problems = []
        missing = [f for f in REQUIRED_FIELDS if house.get(f) is None]
        if missing:
            problems.append("missing required fields: " + ", ".join(missing))
            return problems

        rules = [
            (house["sqft_living"] <= 0, "living area must be greater than zero"),
            (house["sqft_lot"] <= 0, "lot size must be greater than zero"),
            (not 0 <= house["bedrooms"] <= 15, "bedrooms must be between 0 and 15"),
            (not 0 <= house["bathrooms"] <= 10, "bathrooms must be between 0 and 10"),
            (not 1 <= house["floors"] <= 4, "floors must be between 1 and 4"),
            (house["waterfront"] not in (0, 1), "waterfront must be 0 or 1"),
            (not 0 <= house["view"] <= 4, "view rating must be between 0 and 4"),
            (not 1 <= house["condition"] <= 5, "condition rating must be between 1 and 5"),
            (house["sqft_basement"] < 0, "basement area cannot be negative"),
            (house["sqft_basement"] > house["sqft_living"],
             "basement area cannot exceed total living area"),
            (not 1850 <= house["yr_built"] <= P.REFERENCE_YEAR,
             f"year built must be between 1850 and {P.REFERENCE_YEAR}"),
        ]
        problems += [msg for bad, msg in rules if bad]
        return problems

    def _frame(self, house: dict) -> pd.DataFrame:
        d = dict(house)
        d.setdefault("yr_renovated", np.nan)
        d.setdefault("sqft_above", d["sqft_living"] - d["sqft_basement"])
        d["zipcode"] = str(d["zipcode"])
        return P.engineer_features(pd.DataFrame([d]))

    # -- the pieces of the dossier ----------------------------------------
    def segment_of(self, engineered: pd.DataFrame) -> str | None:
        """Day 7's market segment, if the clustering artifacts are present."""
        if self.cluster_pipe is None or self.cluster_cfg is None:
            return None
        label = int(self.cluster_pipe.predict(engineered[self.cluster_cfg["features"]])[0])
        names = {int(k): v for k, v in self.cluster_cfg["names"].items()}
        return names.get(label, f"cluster {label}")

    @staticmethod
    def _display(name: str, raw: pd.Series):
        """Show a feature value the way a person would say it, with its unit."""
        if name == "zipcode_te":
            return str(raw["zipcode"])
        if name == "city_te":
            return str(raw["city"])
        v = raw[name]
        if name in ("sqft_living", "sqft_lot", "sqft_basement", "sqft_per_room"):
            return f"{int(round(float(v))):,} sqft"
        if name in ("house_age", "years_since_reno"):
            return f"{int(round(float(v)))} years"
        if name == "view":
            return f"{int(v)} out of 4"
        if name == "condition":
            return f"{int(v)} out of 5"
        if name in ("waterfront", "has_basement", "was_renovated"):
            return "yes" if float(v) else "no"
        if name == "basement_ratio":
            return f"{100 * float(v):.0f}% of the floor area"
        return f"{float(v):g}"

    def drivers(self, engineered: pd.DataFrame, top_k: int = 5) -> list[dict]:
        """Top SHAP contributions for this house, converted to percentage effects.

        SHAP values are additive in log space, so exp(phi) - 1 is the approximate
        percentage effect of that feature on the predicted price. The two logged area
        columns are folded back into their raw counterparts first (see MERGE_INTO).
        """
        pre = self.model.named_steps["pre"]
        z = pre.transform(engineered[self.features])
        phi = dict(zip(self.output_order, np.asarray(self.explainer.shap_values(z))[0]))

        for source, target in MERGE_INTO.items():
            if source in phi and target in phi:
                phi[target] += phi.pop(source)

        raw = engineered.iloc[0]
        out = []
        for name, value in sorted(phi.items(), key=lambda t: -abs(t[1])):
            out.append({
                "feature": name,
                "label": READABLE.get(name, name),
                "value": self._display(name, raw),
                "pct_effect": round(100 * (np.exp(value) - 1), 1),
            })
        return out[:top_k]

    def checks(self, house: dict, engineered: pd.DataFrame, price: float,
               segment: str | None) -> list[str]:
        """Deterministic sanity checks, run in Python before any LLM sees the case.

        The language model is not asked to judge whether a valuation is plausible —
        it is told which of these fired. A rule that runs every time is worth more
        than a model that notices sometimes.
        """
        flags = []
        ref = self.ref

        if house["waterfront"] == 1:
            flags.append(
                "Waterfront property: the training data contains very few of these, "
                "so this valuation rests on almost no comparable sales."
            )

        if ref:
            if str(house["zipcode"]) not in set(ref.get("known_zipcodes", [])):
                flags.append(
                    f"Zip code {house['zipcode']} does not appear in the training data. "
                    "Location has been replaced by the market-wide average, which is the "
                    "single largest driver in the model — treat this valuation as unreliable."
                )
            if str(house["city"]) not in set(ref.get("known_cities", [])):
                flags.append(
                    f"City '{house['city']}' does not appear in the training data; the "
                    "market-wide average was used instead."
                )
            if "sqft_q99" in ref and house["sqft_living"] > ref["sqft_q99"]:
                flags.append(
                    f"At {house['sqft_living']:,} sqft this house is larger than 99% of the "
                    "training data. The model cannot predict above the range it was trained "
                    "on, so this figure is likely to be too low."
                )
            if "price_q10" in ref and price < ref["price_q10"]:
                flags.append(
                    "This valuation is in the cheapest tenth of the market, where the model "
                    "is known to be optimistic by roughly 12%. Treat it as an upper bound."
                )
            if "price_q90" in ref and price > ref["price_q90"]:
                flags.append(
                    "This valuation is in the most expensive tenth of the market, where the "
                    "model is systematically conservative. Treat it as a floor."
                )
            zip_ppsf = ref.get("zip_ppsf_median", {}).get(str(house["zipcode"]))
            if zip_ppsf:
                ppsf = price / house["sqft_living"]
                if ppsf > 1.75 * zip_ppsf or ppsf < 0.6 * zip_ppsf:
                    flags.append(
                        f"The implied price per square foot (${ppsf:,.0f}) is far from the "
                        f"median for this zip code (${zip_ppsf:,.0f})."
                    )

        seg_err = (self.config.get("segment_MedAPE") or {}).get(segment)
        worst = max((self.config.get("segment_MedAPE") or {}).values(), default=None)
        if seg_err and worst and seg_err == worst:
            flags.append(
                f"'{segment}' is the segment this model handles worst "
                f"(typical error {seg_err:.0f}% against about "
                f"{min(self.config['segment_MedAPE'].values()):.0f}% for the easiest). "
                "Use the valuation for screening, not as a figure to quote a client."
            )
        return flags

    # -- the public entry point -------------------------------------------
    def evidence(self, house: dict, top_k: int = 5) -> dict:
        """One house in, one fully-computed dossier out.

        Raises ValueError on invalid input rather than returning a confident number
        for a house that cannot exist.
        """
        problems = self.validate(house)
        if problems:
            raise ValueError("; ".join(problems))

        engineered = self._frame(house)
        pred_log = float(self.model.predict(engineered[self.features])[0])
        price = float(np.expm1(pred_log))

        segment = self.segment_of(engineered)
        seg_err = (self.config.get("segment_MedAPE") or {}).get(segment)

        return {
            "model_name": self.config["model_name"],
            "house": {k: house[k] for k in REQUIRED_FIELDS},
            "house_age": int(engineered.iloc[0]["house_age"]),
            "predicted_price": round(price, -2),
            "range_low": round(price / (1 + self.hi_pct), -2),
            "range_high": round(price / (1 + self.lo_pct), -2),
            "price_per_sqft": round(price / house["sqft_living"]),
            "typical_error_pct": round(self.config["test_MedAPE_%"], 1),
            "within_10pct_of_sale_price": round(self.config["test_PPE10_%"]),
            "segment": segment,
            "segment_typical_error_pct": round(seg_err, 1) if seg_err else None,
            "drivers": self.drivers(engineered, top_k=top_k),
            "flags": self.checks(house, engineered, price, segment),
        }
