"""
preprocessing.py — the single source of truth for feature engineering.

Why this lives in app/ and not inside the notebook
--------------------------------------------------
The Streamlit app has to transform a single user-entered house in
EXACTLY the same way the training data was transformed. If the transformer
classes were defined inside a notebook, joblib could not un-pickle them in the
app (pickle stores the import path of a class, not its code).

Putting them in an importable module means the notebook and the app run the
same code. Any preprocessing bug is therefore a bug in both places, not a
silent mismatch that only shows up as bad predictions in the demo.

Usage
-----
    from preprocessing import engineer_features, build_preprocessor

    df  = engineer_features(pd.read_csv("Data/data_clean.csv"))
    pre = build_preprocessor()
    pre.fit(X_train, y_train)          # fit on TRAIN ONLY
    Z   = pre.transform(X_test)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# The dataset covers May–July 2014, so "now" is 2014 for age calculations.
REFERENCE_YEAR = 2014

# Columns that must never reach a model.
#   price          — the target
#   price_per_sqft — price / sqft_living: contains the target directly (leakage)
#   date           — only 10 weeks of data, no seasonal signal to extract
#   yr_built, yr_renovated, effective_year — superseded by the age features
LEAKY_OR_DEAD = ["price", "price_per_sqft", "date",
                 "yr_built", "yr_renovated", "effective_year"]

# NOTE (verified in Notebooks/05_features.ipynb): `age_effective` was removed
# from this list because it is *identical* to `years_since_reno` for every row
# (corr = 1.000, not 0.999). Two perfectly collinear columns give Linear
# Regression an infinite number of equally good coefficient pairs, which makes
# the coefficients — the thing you explain in the defense — meaningless.
NUMERIC_FEATURES = [
    "bedrooms", "bathrooms", "sqft_living", "sqft_lot", "floors",
    "waterfront", "view", "condition", "sqft_basement",
    "house_age", "was_renovated",
    "years_since_reno", "has_basement", "basement_ratio",
    "bath_per_bed", "sqft_per_room", "log_sqft_living", "log_sqft_lot",
]

TARGET_ENCODE_FEATURES = ["zipcode", "city"]

ALL_FEATURES = NUMERIC_FEATURES + TARGET_ENCODE_FEATURES


# --------------------------------------------------------------------------
# 1. Row-wise feature engineering
# --------------------------------------------------------------------------
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add engineered columns.

    Every feature here is computed from ONE ROW ONLY. Nothing looks at another
    row, at a group mean, or at the target. That is what makes this function
    safe to call before the train/test split — and safe to call on a single
    house typed into the Streamlit app.

    Anything that needs a group statistic (e.g. the median price per sqft of a
    zip code) is NOT here. It lives in SmoothedTargetEncoder, which is fitted
    inside the pipeline on training data only.
    """
    d = df.copy()

    if "house_age" not in d:
        d["house_age"] = REFERENCE_YEAR - d["yr_built"]

    # Renovation recency. A never-renovated house is given its full age, which
    # is the honest reading of "years since the last time this was renewed".
    # DataFrame.get()'s stub keeps `| None` in its return type even with a non-None
    # default supplied, so pyright can't see that yr_reno is always a real Series here.
    yr_reno = d.get("yr_renovated", pd.Series(np.nan, index=d.index))
    renovated = yr_reno.notna() & (yr_reno > 0)  # pyright: ignore[reportOptionalMemberAccess, reportOptionalOperand]
    d["was_renovated"] = renovated.astype(int)
    d["years_since_reno"] = np.where(
        renovated, REFERENCE_YEAR - yr_reno.fillna(REFERENCE_YEAR), d["house_age"]  # pyright: ignore[reportOptionalMemberAccess]
    )
    d["age_effective"] = d["years_since_reno"]

    # Basement. Section 3 of the business report: below-grade space is worth
    # less than above-grade space, so the model needs to see it separately.
    d["has_basement"] = (d["sqft_basement"] > 0).astype(int)
    d["basement_ratio"] = d["sqft_basement"] / d["sqft_living"].replace(0, np.nan)

    # Layout quality, not layout quantity.
    d["bath_per_bed"] = d["bathrooms"] / d["bedrooms"].replace(0, np.nan)
    d["sqft_per_room"] = d["sqft_living"] / (
        d["bedrooms"].fillna(0) + d["bathrooms"].fillna(0)
    ).replace(0, np.nan)

    # Both areas are strongly right-skewed. Logging them makes the
    # relationship with log(price) roughly linear.
    d["log_sqft_living"] = np.log1p(d["sqft_living"])
    d["log_sqft_lot"] = np.log1p(d["sqft_lot"])

    # A handful of divisions above can produce NaN (0 bedrooms, 0 sqft).
    # Fill with the neutral value rather than dropping the row.
    for col in ["basement_ratio", "bath_per_bed", "sqft_per_room"]:
        d[col] = d[col].replace([np.inf, -np.inf], np.nan)
    d["basement_ratio"] = d["basement_ratio"].fillna(0.0)
    d["bath_per_bed"] = d["bath_per_bed"].fillna(d["bathrooms"])
    d["sqft_per_room"] = d["sqft_per_room"].fillna(d["sqft_living"])

    # sqft_above is dropped: sqft_above == sqft_living - sqft_basement exactly,
    # so keeping all three gives a perfectly collinear set. Verified in
    # Notebooks/05_features.ipynb.
    return d


# --------------------------------------------------------------------------
# 2. Target encoding — the part that can leak
# --------------------------------------------------------------------------
class SmoothedTargetEncoder(BaseEstimator, TransformerMixin):
    """
    Replace a high-cardinality category (zipcode: 77 levels, city: 44) with the
    mean target of that category.

    Two safeguards, both necessary:

    1. **Smoothing.** A zip code with 3 sales should not be trusted as much as
       one with 142. Each category mean is pulled toward the global mean with
       weight n / (n + m). With m = 20, a category needs 20 observations before
       it is trusted half as much as the global average. This is exactly the
       credibility-weighting idea from actuarial ratemaking:
           Z = n / (n + k)
       and it is the same defence against thin cells.

    2. **Out-of-fold encoding on the training set.** If a row's own price helps
       compute the mean that becomes that row's feature, the feature partly
       contains the answer. The model then over-trusts it and test performance
       collapses. So during `fit_transform`, each training row is encoded using
       a mapping built from the OTHER folds only. `transform` (used for the
       test set and for the app) uses the full-training mapping — which is
       correct, because test rows contributed nothing to it.

    Unseen categories at prediction time fall back to the global training mean.
    """

    def __init__(self, cols=None, smoothing: float = 20.0, n_splits: int = 5,
                 random_state: int = 42):
        self.cols = cols
        self.smoothing = smoothing
        self.n_splits = n_splits
        self.random_state = random_state

    # -- helpers ----------------------------------------------------------
    def _cols(self, X):
        return list(X.columns) if self.cols is None else list(self.cols)

    def _build_map(self, s: pd.Series, y: pd.Series, prior: float) -> dict:
        stats = y.groupby(s).agg(["mean", "count"])
        weight = stats["count"] / (stats["count"] + self.smoothing)
        # pandas-stubs resolves this arithmetic to NDArray instead of Series; it is a
        # Series at runtime (weight and stats["mean"] both are), so .to_dict() is valid.
        return (weight * stats["mean"] + (1 - weight) * prior).to_dict()  # pyright: ignore[reportAttributeAccessIssue]

    # -- sklearn API ------------------------------------------------------
    def fit(self, X, y):
        X = pd.DataFrame(X).reset_index(drop=True)
        y = pd.Series(np.asarray(y)).reset_index(drop=True)
        self.feature_names_in_ = self._cols(X)
        self.prior_ = float(y.mean())
        self.maps_ = {c: self._build_map(X[c], y, self.prior_)  # pyright: ignore[reportArgumentType]
                      for c in self.feature_names_in_}
        return self

    def transform(self, X):
        X = pd.DataFrame(X)
        out = pd.DataFrame(index=X.index)
        for c in self.feature_names_in_:
            out[f"{c}_te"] = X[c].map(self.maps_[c]).astype(float).fillna(self.prior_)  # pyright: ignore[reportArgumentType]
        return out.values

    def fit_transform(self, X, y=None, **fit_params):
        """Out-of-fold encoding for the training set. See class docstring."""
        if y is None:
            raise ValueError("SmoothedTargetEncoder requires y during fit.")
        X = pd.DataFrame(X).reset_index(drop=True)
        y = pd.Series(np.asarray(y)).reset_index(drop=True)
        self.fit(X, y)

        oof = pd.DataFrame(index=X.index, columns=
                           [f"{c}_te" for c in self.feature_names_in_], dtype=float)
        kf = KFold(n_splits=self.n_splits, shuffle=True,
                   random_state=self.random_state)
        for tr_idx, va_idx in kf.split(X):
            prior = float(y.iloc[tr_idx].mean())
            for c in self.feature_names_in_:
                m = self._build_map(X[c].iloc[tr_idx], y.iloc[tr_idx], prior)
                oof.loc[va_idx, f"{c}_te"] = (
                    X[c].iloc[va_idx].map(m).astype(float).fillna(prior).values
                )
        return oof.values

    def get_feature_names_out(self, input_features=None):
        return np.array([f"{c}_te" for c in self.feature_names_in_])


# --------------------------------------------------------------------------
# 3. The pipeline
# --------------------------------------------------------------------------
def build_preprocessor(smoothing: float = 20.0) -> ColumnTransformer:
    """
    Numeric columns -> StandardScaler.
    zipcode / city   -> SmoothedTargetEncoder, then scaled with everything else.

    Returned unfitted. Call .fit(X_train, y_train). Because every statistic
    (means, standard deviations, category maps) is learned inside .fit, calling
    .transform(X_test) cannot see test data. That is the whole point.
    """
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("te", Pipeline([
                ("encode", SmoothedTargetEncoder(cols=TARGET_ENCODE_FEATURES,
                                                 smoothing=smoothing)),
                ("scale", StandardScaler()),
            ]), TARGET_ENCODE_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def feature_names(preprocessor: ColumnTransformer) -> list[str]:
    """Column names of the transformed matrix, in order."""
    return NUMERIC_FEATURES + [f"{c}_te" for c in TARGET_ENCODE_FEATURES]
