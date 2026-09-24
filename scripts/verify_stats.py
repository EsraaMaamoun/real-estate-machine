"""
verify_stats.py — the paired comparisons, re-run against the CURRENT artifacts.

An independent re-check, not the source of any quoted number. The GB-vs-XGB figures
quoted in the README, the deck, the app and the Kaggle notebook all come from notebook 09,
section 8 (gap -0.24 pp, 95% bootstrap CI [-0.92, +0.40], Wilcoxon p = 0.12), the same
run as Models/model_comparison.csv.

This script recomputes both comparisons on the model that is actually in Models/ and an
XGBoost refitted with the parameters the grid search selected (learning_rate 0.03,
max_depth 4, n_estimators 800). The refit is a second fit of the same configuration and
lands at 10.95% rather than 10.78%, so its gap and p-value differ from notebook 09's;
its verdict is the same: not distinguishable. GB vs Ridge reproduces notebook 09 exactly.

Writes reports/slides/stats_facts.json.
"""
import json
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "app"))
import preprocessing as P  # noqa: E402

raw = pd.read_csv(ROOT / "Data" / "data_clean.csv", dtype={"zipcode": str})
df = P.engineer_features(raw)
split = pd.read_csv(ROOT / "Data" / "split_indices.csv", index_col="row")["split"]
tr = split.values == "train"

cfg = joblib.load(ROOT / "Models" / "regressor_config.pkl")
gb = joblib.load(ROOT / "Models" / "regressor.pkl")

X, y = df[cfg["features"]], np.log1p(df["price"])
X_tr, X_te, y_tr, y_te = X[tr], X[~tr], y[tr], y[~tr]
price_te = np.expm1(y_te).values

def ape(pipe):
    p = np.expm1(pipe.predict(X_te))
    return np.abs(p - price_te) / price_te

a_gb = ape(gb)

ridge = Pipeline([("pre", P.build_preprocessor(smoothing=20)),
                  ("model", Ridge(alpha=100))]).fit(X_tr, y_tr)
a_ridge = ape(ridge)

import xgboost as xgb  # noqa: E402
xgbp = Pipeline([("pre", P.build_preprocessor(smoothing=20)),
                 ("model", xgb.XGBRegressor(learning_rate=0.03, max_depth=4,
                                            n_estimators=800, random_state=42,
                                            n_jobs=-1, tree_method="hist"))]).fit(X_tr, y_tr)
a_xgb = ape(xgbp)

rng = np.random.default_rng(42)
IDX = [rng.integers(0, len(a_gb), len(a_gb)) for _ in range(2000)]

def compare(a, b, label):
    diff = 100 * (np.median(a) - np.median(b))
    boot = [100 * (np.median(a[i]) - np.median(b[i])) for i in IDX]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    _, p = wilcoxon(a, b)
    verdict = "real" if (hi < 0 and p < 0.05) else "not distinguishable"
    print(f"{label}: {diff:+.2f} pp   CI [{lo:+.2f}, {hi:+.2f}]   p = {p:.2g}   -> {verdict}")
    return {"diff_pp": float(diff), "ci_lo": float(lo), "ci_hi": float(hi),
            "p": float(p), "verdict": verdict}

S = {}
print(f"GB  MedAPE {100*np.median(a_gb):.2f}%   "
      f"Ridge {100*np.median(a_ridge):.2f}%   XGB {100*np.median(a_xgb):.2f}%\n")
S["medape_gb"] = float(100 * np.median(a_gb))
S["medape_ridge"] = float(100 * np.median(a_ridge))
S["medape_xgb"] = float(100 * np.median(a_xgb))
S["vs_ridge"] = compare(a_gb, a_ridge, "GB vs Ridge")
S["vs_xgb"] = compare(a_gb, a_xgb, "GB vs XGB  ")

# The two metrics XGBoost wins, straight from her own comparison table.
comp = pd.read_csv(ROOT / "Models" / "model_comparison.csv", index_col=0)
if "XGB (tuned)" in comp.index:
    for k, col in [("r2", "R2_log"), ("mape", "MAPE_%"), ("mae", "MAE_$")]:
        S[f"gb_{k}"] = float(comp.loc["GB (tuned)", col])
        S[f"xgb_{k}"] = float(comp.loc["XGB (tuned)", col])
    print(f"\nR2   GB {S['gb_r2']:.4f}  XGB {S['xgb_r2']:.4f}   <- XGB wins")
    print(f"MAPE GB {S['gb_mape']:.2f}%  XGB {S['xgb_mape']:.2f}%   <- XGB wins")

# IAAO for all three, so the tie-break slide is computed rather than remembered.
def iaao(pipe):
    pred = np.expm1(pipe.predict(X_te))
    r = pred / price_te
    med = float(np.median(r))
    return {"median_ratio": med,
            "cod": float(100 * np.mean(np.abs(r - med)) / med),
            "prd": float(np.mean(r) / (np.sum(pred) / np.sum(price_te)))}

S["iaao"] = {"GB (tuned)": iaao(gb), "Ridge": iaao(ridge), "XGB (tuned)": iaao(xgbp)}
print("\nIAAO          median ratio     COD      PRD")
for name, v in S["iaao"].items():
    flag = ("PASS" if 0.90 <= v["median_ratio"] <= 1.10 else "FAIL",
            "PASS" if 5 <= v["cod"] <= 15 else "FAIL",
            "PASS" if 0.98 <= v["prd"] <= 1.03 else "FAIL")
    print(f"  {name:12s} {v['median_ratio']:.3f} {flag[0]}   "
          f"{v['cod']:.2f} {flag[1]}   {v['prd']:.3f} {flag[2]}")

out = ROOT / "reports" / "slides" / "stats_facts.json"
out.write_text(json.dumps(S, indent=1))
print(f"\nwrote {out}")
