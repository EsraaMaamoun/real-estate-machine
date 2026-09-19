"""
train.py — rebuild every model artefact from the cleaned data, with one command.

    python -m src.train              # train, evaluate, print — writes nothing
    python -m src.train --save       # ... and overwrite Models/*.pkl
    python -m src.train --tune       # re-run the grid search instead of using the stored winner

Why this file exists
--------------------
Notebooks 05 and 09 are where the modelling decisions were argued and evidenced.
They are the record of *how the model was chosen*. They are not a good way to
*rebuild* it: doing that means opening two notebooks and running forty cells in
the right order, on a machine set up the right way, and trusting that nobody
edited a cell in between.

This script is the rebuild path. It reads Data/data_clean.csv and rewrites every
.pkl in Models/ deterministically. If it runs clean, the model in Models/ is
reproducible; if it cannot, the model is a one-off artefact that happens to sit
on one laptop.

That is the difference the script is here to make. The notebooks keep the
reasoning; this keeps the result reproducible.

Safety
------
By default this script writes NOTHING. It trains, scores, compares against the
numbers recorded in REFERENCE, and exits non-zero if they have drifted. Pass
--save only when you actually intend to replace the deployed artefacts.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, KFold, train_test_split
from sklearn.pipeline import Pipeline

# --------------------------------------------------------------------------
# Paths and configuration
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "Data"
MODELS = ROOT / "Models"

# preprocessing.py is imported from app/, not copied here, and that is deliberate.
# pickle stores a class by its import path, not its code: every existing
# Models/*.pkl refers to `preprocessing.SmoothedTargetEncoder`. Re-defining that
# class anywhere else would produce artefacts the Streamlit app cannot un-pickle.
# One definition, imported by both the notebooks and this script, is the only
# arrangement in which training and serving cannot silently disagree.
sys.path.insert(0, str(ROOT / "app"))
import preprocessing as P  # noqa: E402

RANDOM_STATE = 42
TEST_SIZE = 0.20
SMOOTHING = 20  # target-encoding smoothing used by the champion pipeline (notebook 09)

# The winner of the notebook 09 grid search. --tune re-derives these from scratch.
CHAMPION_PARAMS = {
    "n_estimators": 600,
    "learning_rate": 0.05,
    "max_depth": 3,
}

TUNING_GRID = {
    "model__n_estimators": [300, 600],
    "model__learning_rate": [0.05, 0.1],
    "model__max_depth": [2, 3, 4],
}

# Recorded from the executed notebook 09. The script checks itself against these:
# a rebuild that produces different numbers is a bug, not a new result.
REFERENCE = {
    "R2_log": 0.8627,
    "MedAPE_%": 10.54,
    "MAPE_%": 14.58,
    "PPE10_%": 47.87,
    "train_R2": 0.9170,
}
TOLERANCE = {"R2_log": 0.005, "MedAPE_%": 0.15, "MAPE_%": 0.20,
             "PPE10_%": 1.0, "train_R2": 0.010}


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
def load_data() -> pd.DataFrame:
    """Cleaned sales + the row-wise engineered features. No group statistics here."""
    path = DATA / "data_clean.csv"
    if not path.exists():
        raise SystemExit(
            f"Missing {path}.\nRun Notebooks/02_cleaning.ipynb first — this script "
            f"starts from clean data, it does not clean."
        )
    raw = pd.read_csv(path, dtype={"zipcode": str})
    return P.engineer_features(raw)


def load_split(df: pd.DataFrame) -> np.ndarray:
    """
    The fixed train/test split, as a boolean 'is_train' mask.

    Data/split_indices.csv is the contract every notebook from 05 onward honours:
    it is what makes the clustering, the classifier and the regressor comparable,
    because they are all scored on the same 869 houses. If the file is missing it
    is regenerated from the same seed — but a regenerated split silently
    invalidates comparisons with numbers already written into the report, so the
    script says so loudly rather than quietly carrying on.
    """
    path = DATA / "split_indices.csv"
    if path.exists():
        split = pd.read_csv(path, index_col="row")["split"]
        if len(split) != len(df):
            raise SystemExit(
                f"{path.name} has {len(split)} rows but the data has {len(df)}. "
                f"The split file and the cleaned data are out of step — regenerate "
                f"both, or restore the matching data_clean.csv."
            )
        return (split.values == "train")

    print(f"!  {path.name} not found — regenerating from seed {RANDOM_STATE}.")
    print("!  Numbers already published in reports/ were computed on the old split.")
    idx_train, _ = train_test_split(
        df.index, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )
    mask = df.index.isin(idx_train)
    pd.Series(np.where(mask, "train", "test"), index=df.index,
              name="split").to_frame().to_csv(path, index_label="row")
    return mask


def load_segments(is_train: np.ndarray) -> np.ndarray | None:
    """
    Market segment per test house, from notebook 06's clustering.

    Optional: the regressor does not use the segment as a feature. But the app's
    explanation panel reads config['segment_MedAPE'] to tell the user how much to
    trust a valuation for this kind of house — 'Premium View Property' carries
    roughly twice the error of the others, and hiding that would be the wrong
    kind of confident. So it is computed when the file is there.
    """
    path = DATA / "data_clustered.csv"
    if not path.exists():
        return None
    return pd.read_csv(path)["segment"].to_numpy()[~is_train]


def segment_errors(segments, pred_price, price_test) -> dict:
    """Median absolute percentage error within each market segment."""
    ape = 100 * np.abs(pred_price - price_test) / price_test
    return (pd.DataFrame({"segment": segments, "ape": ape})
            .groupby("segment")["ape"].median().to_dict())


# --------------------------------------------------------------------------
# Metrics — identical to notebooks 08 and 09. Do not edit one copy alone.
# --------------------------------------------------------------------------
def score(y_true_log, y_pred_log) -> dict:
    """
    Errors are reported in dollars, not in log space.

    The model is trained on log1p(price) because price is right-skewed, but an
    R^2 of 0.86 on a logged target means nothing to a business reader. Everything
    below np.expm1 is back in the units a person actually thinks in.
    """
    true_d = np.expm1(y_true_log)
    pred_d = np.expm1(y_pred_log)
    ape = np.abs(pred_d - true_d) / true_d
    return {
        "R2_log": r2_score(y_true_log, y_pred_log),
        "RMSE_log": float(np.sqrt(mean_squared_error(y_true_log, y_pred_log))),
        "MAE_$": mean_absolute_error(true_d, pred_d),
        "RMSE_$": float(np.sqrt(mean_squared_error(true_d, pred_d))),
        "MedAPE_%": 100 * float(np.median(ape)),
        "MAPE_%": 100 * float(ape.mean()),
        "PPE10_%": 100 * float((ape <= 0.10).mean()),
        "PPE20_%": 100 * float((ape <= 0.20).mean()),
    }


def iaao(pred: np.ndarray, actual: np.ndarray) -> dict:
    """
    The IAAO ratio study — the standard mass-appraisal authorities use.

    An accurate model can still be an unfair one: PRD detects regressivity, i.e.
    cheap houses over-valued and expensive ones under-valued, which is invisible
    in MedAPE. This is what broke the tie between GB and XGB in notebook 09.

    Acceptable bands: median ratio 0.90-1.10, COD <= 15, PRD 0.98-1.03.
    """
    ratio = pred / actual
    median_ratio = float(np.median(ratio))
    return {
        "median_ratio": median_ratio,
        "cod": float(100 * np.mean(np.abs(ratio - median_ratio)) / median_ratio),
        "prd": float(ratio.mean() / (pred.sum() / actual.sum())),
    }


def iaao_verdict(m: dict) -> str:
    checks = [
        ("ratio", 0.90 <= m["median_ratio"] <= 1.10),
        ("COD", m["cod"] <= 15.0),
        ("PRD", 0.98 <= m["prd"] <= 1.03),
    ]
    failed = [name for name, ok in checks if not ok]
    return "PASS (all three)" if not failed else f"FAIL on {', '.join(failed)}"


# --------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------
def build_pipeline(params: dict) -> Pipeline:
    """
    Preprocessing and model as ONE object.

    Keeping them together is what stops the classic production bug: a scaler
    fitted in a notebook, a model saved separately, and an app that applies them
    in the wrong order or with the wrong statistics. Fitting this pipeline fits
    the encoder on training rows only; predicting applies exactly what was fitted.
    """
    return Pipeline([
        ("pre", P.build_preprocessor(smoothing=SMOOTHING)),
        ("model", GradientBoostingRegressor(random_state=RANDOM_STATE, **params)),
    ])


def tune(X_train, y_train) -> dict:
    """Re-derive the hyperparameters instead of trusting the stored ones."""
    kf = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    gs = GridSearchCV(build_pipeline({}), TUNING_GRID, cv=kf,
                      scoring="r2", n_jobs=-1, refit=False)
    t0 = time.time()
    gs.fit(X_train, y_train)
    best = {k.replace("model__", ""): v for k, v in gs.best_params_.items()}
    n = len(gs.cv_results_["params"])
    print(f"   {n} combinations x 5 folds in {time.time() - t0:.0f}s")
    print(f"   best CV R2 = {gs.best_score_:.4f}   params = {best}")
    if best != CHAMPION_PARAMS:
        print(f"   !  differs from the stored champion {CHAMPION_PARAMS}")
    return best


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--save", action="store_true",
                    help="overwrite Models/*.pkl (default: write nothing)")
    ap.add_argument("--tune", action="store_true",
                    help="re-run the grid search instead of using the stored winner")
    args = ap.parse_args(argv)

    print("=" * 66)
    print("Real Estate Machine — model rebuild")
    print("=" * 66)

    # 1. Data ---------------------------------------------------------------
    df = load_data()
    is_train = load_split(df)

    X = df[P.ALL_FEATURES]
    y = np.log1p(df["price"])
    X_train, X_test = X[is_train], X[~is_train]
    y_train, y_test = y[is_train], y[~is_train]
    price_test = np.expm1(y_test).to_numpy()

    print(f"\n1. Data      {len(df):,} clean sales -> "
          f"{len(X_train):,} train / {len(X_test):,} test, "
          f"{len(P.ALL_FEATURES)} features")

    # 2. Hyperparameters ----------------------------------------------------
    if args.tune:
        print("\n2. Tuning    grid search (this takes a minute)")
        params = tune(X_train, y_train)
    else:
        params = dict(CHAMPION_PARAMS)
        print(f"\n2. Params    {params}  (from notebook 09; --tune to re-derive)")

    # 3. Fit ----------------------------------------------------------------
    pipe = build_pipeline(params)
    t0 = time.time()
    pipe.fit(X_train, y_train)
    print(f"\n3. Fit       GradientBoostingRegressor in {time.time() - t0:.1f}s")

    # 4. Evaluate -----------------------------------------------------------
    pred_log = pipe.predict(X_test)
    pred_price = np.expm1(pred_log)
    metrics = score(y_test, pred_log)
    metrics["train_R2"] = r2_score(y_train, pipe.predict(X_train))
    ratio = iaao(pred_price, price_test)

    print("\n4. Test set  (869 sales the model has never seen)")
    print(f"   R2 (log)            {metrics['R2_log']:.4f}")
    print(f"   Median abs % error  {metrics['MedAPE_%']:.2f}%   <- the headline number")
    print(f"   Mean abs % error    {metrics['MAPE_%']:.2f}%")
    print(f"   Within +/-10%       {metrics['PPE10_%']:.1f}% of houses")
    print(f"   MAE                 ${metrics['MAE_$']:,.0f}")
    print(f"   Train R2            {metrics['train_R2']:.4f}   "
          f"(gap {metrics['train_R2'] - metrics['R2_log']:+.4f} — overfit check)")

    print(f"\n   IAAO ratio study    ratio {ratio['median_ratio']:.3f} | "
          f"COD {ratio['cod']:.2f} | PRD {ratio['prd']:.3f}  ->  {iaao_verdict(ratio)}")

    pct_err = (pred_price - price_test) / price_test
    lo, hi = np.percentile(pct_err, [10, 90])
    print(f"   80% interval        {100 * lo:+.1f}% to {100 * hi:+.1f}%")

    # Per-segment error — the app shows this, so it must survive a rebuild.
    segments = load_segments(is_train)
    if segments is not None:
        seg_med = segment_errors(segments, pred_price, price_test)
        print("\n   By market segment (median abs % error)")
        for name, err in sorted(seg_med.items(), key=lambda kv: kv[1]):
            print(f"     {name:<28} {err:5.2f}%")
    else:
        seg_med = None
        print("\n   !  Data/data_clustered.csv missing — segment errors not recomputed.")

    # 5. Self-check ---------------------------------------------------------
    print("\n5. Check     against the numbers recorded in notebook 09")
    drift = []
    for key, expected in REFERENCE.items():
        actual = metrics[key]
        delta = actual - expected
        ok = abs(delta) <= TOLERANCE[key]
        print(f"   {'ok  ' if ok else 'DRIFT'} {key:<10} "
              f"got {actual:8.4f}   expected {expected:8.4f}   ({delta:+.4f})")
        if not ok:
            drift.append(key)

    if drift:
        print(f"\n   {len(drift)} metric(s) drifted: {', '.join(drift)}")
        print("   The data, the split or the library versions have changed.")
        print("   Do NOT --save until you know which.")
        return 1

    print("\n   Reproduced. This model is rebuildable from source data.")

    # 6. Save ---------------------------------------------------------------
    if not args.save:
        print("\n6. Save      skipped (pass --save to overwrite Models/*.pkl)")
        print("=" * 66)
        return 0

    MODELS.mkdir(exist_ok=True)

    # Never let a rebuild silently remove a key the app depends on. If the
    # segment errors could not be recomputed, carry forward what is already
    # there rather than shipping a config that makes the app's explanation
    # panel fall back to generic text.
    if seg_med is None:
        existing = MODELS / "regressor_config.pkl"
        if existing.exists():
            seg_med = joblib.load(existing).get("segment_MedAPE")
            if seg_med:
                print("   carrying forward segment_MedAPE from the previous config")

    joblib.dump(pipe, MODELS / "regressor.pkl")

    config = {
        "model_name": "GB (tuned)",
        "sklearn_params": params,
        "target": "log1p(price)",
        "back_transform": "np.expm1",
        "features": P.ALL_FEATURES,
        "output_order": P.feature_names(pipe.named_steps["pre"]),
        "smoothing": SMOOTHING,
        "random_state": RANDOM_STATE,
        "headline_metric": "MedAPE_%",
        "test_MedAPE_%": metrics["MedAPE_%"],
        "test_MAPE_%": metrics["MAPE_%"],
        "test_R2_log": metrics["R2_log"],
        "test_PPE10_%": metrics["PPE10_%"],
        "interval_pct_10_90": [float(lo), float(hi)],
        "iaao": ratio,
        "segment_MedAPE": seg_med,
        "known_weaknesses": [
            "over-values the cheapest decile (median +12%)",
            "under-values the top decile - trees cannot extrapolate above the training range",
            "Premium View Property segment is about twice the error of the others",
        ],
        "rebuilt_by": "src/train.py",
        "rebuilt_at": pd.Timestamp.now().isoformat(timespec="seconds"),
    }
    joblib.dump(config, MODELS / "regressor_config.pkl")

    # A small background sample so the app can explain a single house with SHAP.
    try:
        import shap  # noqa: F401
        pre = pipe.named_steps["pre"]
        bg = pre.transform(X_train.sample(200, random_state=RANDOM_STATE))
        joblib.dump({"background": bg,
                     "feature_names": P.feature_names(pre)},
                    MODELS / "shap_background.pkl")
        shap_note = " + shap_background.pkl"
    except ImportError:
        shap_note = "  (shap not installed — background sample skipped)"

    (MODELS / "last_run.json").write_text(
        json.dumps({"metrics": metrics, "iaao": ratio, "params": params}, indent=2)
    )

    print(f"\n6. Save      regressor.pkl + regressor_config.pkl{shap_note}")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
