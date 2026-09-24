"""
verify_value.py — what the model is worth in money, and how wide its range really is.

Two things the August deck never said:

1. Every figure on it was a percentage. A business audience converts to currency
   or stops listening, so the error is restated in dollars, against two simple
   valuation benchmarks that need no model.

2. The "8 out of 10 houses" band was a single global number, even though the
   deck's own error-by-decile slide shows the error is not uniform. The band is
   recomputed per segment here; the spread between segments is the finding.

Writes reports/slides/value_facts.json and Models/segment_intervals.pkl (used by
the app so the range it quotes matches the range this deck claims).
"""
import json
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "app"))
import preprocessing as P  # noqa: E402

raw = pd.read_csv(ROOT / "Data" / "data_clean.csv", dtype={"zipcode": str})
df = P.engineer_features(raw)
split = pd.read_csv(ROOT / "Data" / "split_indices.csv", index_col="row")["split"]
tr = split.values == "train"

cfg = joblib.load(ROOT / "Models" / "regressor_config.pkl")
model = joblib.load(ROOT / "Models" / "regressor.pkl")

actual = df["price"][~tr].values
pred = np.expm1(model.predict(df[cfg["features"]][~tr]))
ae = np.abs(pred - actual)

V = {"n_train": int(tr.sum()), "n_test": int((~tr).sum())}
V["mae"] = float(ae.mean())
V["medae"] = float(np.median(ae))
V["medape"] = float(100 * np.median(ae / actual))

# --- two valuation benchmarks that need no model ---------------------------
ppsf = (df.loc[tr, "price"] / df.loc[tr, "sqft_living"]).groupby(df.loc[tr, "zipcode"]).median()
rule_ppsf = (df.loc[~tr, "zipcode"].map(ppsf).fillna(ppsf.median())
             * df.loc[~tr, "sqft_living"]).values
zmed = df.loc[tr].groupby("zipcode")["price"].median()
rule_med = df.loc[~tr, "zipcode"].map(zmed).fillna(df.loc[tr, "price"].median()).values

for key, rule, label in [("ppsf", rule_ppsf, "zip price-per-sqft x size"),
                         ("zipmed", rule_med, "zip median price")]:
    e = np.abs(rule - actual)
    V[f"rule_{key}_mae"] = float(e.mean())
    V[f"rule_{key}_medape"] = float(100 * np.median(e / actual))
    V[f"saving_{key}"] = float(e.mean() - ae.mean())
    V[f"saving_{key}_pct"] = float(100 * (1 - ae.mean() / e.mean()))
    V[f"rule_{key}_label"] = label

V["ppe10"] = float(100 * (ae / actual <= 0.10).mean())
V["ppe20"] = float(100 * (ae / actual <= 0.20).mean())

# --- confidence, conditioned on the segment --------------------------------
clu = joblib.load(ROOT / "Models" / "cluster_pipeline.pkl")
ccfg = joblib.load(ROOT / "Models" / "cluster_config.pkl")
names = {int(k): v for k, v in ccfg["names"].items()}
segs = pd.Series([names[int(l)] for l in clu.predict(df[ccfg["features"]])])[~tr].values

pe = 100 * (pred - actual) / actual
res = pd.DataFrame({"pe": pe, "ape": 100 * ae / actual, "actual": actual, "seg": segs})

V["global_lo"], V["global_hi"] = float(np.percentile(pe, 10)), float(np.percentile(pe, 90))
V["global_width"] = V["global_hi"] - V["global_lo"]

bands, intervals = [], {}
for s, g in res.groupby("seg"):
    lo, hi = float(np.percentile(g.pe, 10)), float(np.percentile(g.pe, 90))
    bands.append({"segment": s, "n": int(len(g)), "lo": lo, "hi": hi,
                  "width": hi - lo, "medape": float(g.ape.median()),
                  "median_price": float(g.actual.median())})
    # stored the way explain.py wants it: fractions, low first
    intervals[s] = [lo / 100, hi / 100]
bands.sort(key=lambda b: b["width"])
V["segment_bands"] = bands
V["width_ratio"] = bands[-1]["width"] / bands[0]["width"]

joblib.dump({"global": cfg["interval_pct_10_90"], "by_segment": intervals,
             "built_from_test_rows": int((~tr).sum()),
             "note": "10th-90th percentile of signed percentage error, per market segment"},
            ROOT / "Models" / "segment_intervals.pkl")

# what the band means in money on a median home of that segment
for b in bands:
    b["usd_lo"] = b["median_price"] / (1 + b["hi"] / 100)
    b["usd_hi"] = b["median_price"] / (1 + b["lo"] / 100)

(ROOT / "reports" / "slides" / "value_facts.json").write_text(json.dumps(V, indent=1))

print(f"test rows {V['n_test']:,}   MedAPE {V['medape']:.2f}%")
print(f"  half of valuations land within ${V['medae']:,.0f} of the sale price")
print(f"  mean absolute error ${V['mae']:,.0f}\n")
for k in ("ppsf", "zipmed"):
    print(f"  vs {V[f'rule_{k}_label']:26s} MAE ${V[f'rule_{k}_mae']:,.0f} "
          f"({V[f'rule_{k}_medape']:.1f}%)  ->  saves ${V[f'saving_{k}']:,.0f}/house "
          f"({V[f'saving_{k}_pct']:.0f}%)")
print(f"\nglobal band  {V['global_lo']:+.1f}% / {V['global_hi']:+.1f}%  "
      f"(width {V['global_width']:.0f} pp)")
for b in bands:
    print(f"  {b['segment']:28s} n={b['n']:3d}  {b['lo']:+6.1f}% / {b['hi']:+6.1f}%  "
          f"width {b['width']:4.0f} pp   typical error {b['medape']:.1f}%")
print(f"\nwidest / narrowest = {V['width_ratio']:.1f}x")
print("wrote Models/segment_intervals.pkl")
