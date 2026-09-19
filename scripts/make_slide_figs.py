"""
make_slide_figs.py — the three figures that come straight from the model.

Companion to make_business_figs.py; both draw from scripts/design.py so the deck,
the charts and the live app are one visual system.
"""
import json
import sys
import warnings
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "scripts"))
sys.path.append(str(ROOT / "app"))
import design as D
import preprocessing as P

warnings.filterwarnings("ignore")
D.apply_matplotlib()
OUT = ROOT / "reports" / "slides"
OUT.mkdir(parents=True, exist_ok=True)

raw = pd.read_csv(ROOT / "Data" / "data_clean.csv", dtype={"zipcode": str})
df = P.engineer_features(raw)
split = pd.read_csv(ROOT / "Data" / "split_indices.csv", index_col="row")["split"]
tr = split.values == "train"
cfg = joblib.load(ROOT / "Models" / "regressor_config.pkl")
model = joblib.load(ROOT / "Models" / "regressor.pkl")

# ---------------------------------------------------------------- 1. the skew
fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
clip = 2500
axes[0].hist(np.clip(raw["price"] / 1000, 0, clip), bins=60, color=D.AMBER)
axes[0].set_xlim(0, clip)
axes[0].set_title("Sale price")
axes[0].set_xlabel("thousands of dollars  (tail beyond 2,500 folded into the last bar)")
axes[1].hist(np.log1p(raw["price"]), bins=60, color=D.AMBER)
axes[1].set_title("log(1 + sale price)")
axes[1].set_xlabel("log dollars")
for ax in axes:
    D.bare(ax)
    ax.set_yticks([])
fig.tight_layout(); fig.savefig(OUT / "fig_price_skew.png", dpi=200); plt.close(fig)

# ---------------------------------------------------------------- 2. the segments
clu = joblib.load(ROOT / "Models" / "cluster_pipeline.pkl")
ccfg = joblib.load(ROOT / "Models" / "cluster_config.pkl")
names = {int(k): v for k, v in ccfg["names"].items()}
labels = [names[int(l)] for l in clu.predict(df[ccfg["features"]])]
seg = (df.assign(seg=labels).groupby("seg")
       .agg(n=("price", "size"), median=("price", "median"))
       .sort_values("median"))

fig, ax = plt.subplots(figsize=(11, 3.6))
# One hue: this is magnitude, not identity. The segment the model handles worst is
# picked out in brick, because slide 16 is about to make that its whole point.
colours = [D.BRICK if s == "Premium View Property" else D.STONE for s in seg.index]
ax.barh(seg.index, seg["median"] / 1000, color=colours, height=0.6)
for y, (v, n) in enumerate(zip(seg["median"] / 1000, seg["n"])):
    ax.text(v + 12, y, f"${v:,.0f}k   ({100 * n / len(df):.0f}% of the market)",
            va="center", fontsize=12, color=D.MUTED)
ax.set_xlim(0, seg["median"].max() / 1000 * 1.75)
ax.set_xticks([])
ax.set_title("Four market segments, found by k-means (k = 4)")
D.bare(ax, keep=())
fig.tight_layout(); fig.savefig(OUT / "fig_segments.png", dpi=200); plt.close(fig)

# ---------------------------------------------------------------- 3. error by decile
actual = df["price"][~tr].values
pred = np.expm1(model.predict(df[cfg["features"]][~tr]))
res = pd.DataFrame({"actual": actual, "pred": pred})
res["signed"] = 100 * (res["pred"] - res["actual"]) / res["actual"]
res["decile"] = pd.qcut(res["actual"], 10, labels=False) + 1
dec = res.groupby("decile")["signed"].median()

fig, ax = plt.subplots(figsize=(11, 3.8))
# Diverging: over-valued and under-valued are opposite failures, so they get the
# two poles. The neutral midpoint is the axis itself.
ax.bar(dec.index, dec.values, color=[D.BRICK if b > 0 else D.TEAL for b in dec.values],
       width=0.68)
ax.axhline(0, color=D.MUTED, lw=1)
ax.set_xticks(dec.index)
ax.set_xlabel("price decile  (1 = cheapest houses, 10 = most expensive)")
ax.set_ylabel("median signed error, %")
ax.set_title("Over-valued (brick) at the bottom, under-valued (teal) at the top")
ax.bar_label(ax.containers[0], labels=[f"{v:+.1f}" for v in dec.values],
             padding=4, fontsize=11, color=D.MUTED)
ax.set_ylim(dec.min() - 3.5, dec.max() + 3.5)
D.bare(ax)
fig.tight_layout(); fig.savefig(OUT / "fig_error_by_decile.png", dpi=200); plt.close(fig)

print("wrote fig_price_skew.png, fig_segments.png, fig_error_by_decile.png")
