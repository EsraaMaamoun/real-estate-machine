"""
make_business_figs.py — the new and revised figures for the defence deck.

Reads the three verified fact files (business_facts, value_facts, stats_facts) so
no figure can drift from a number that was actually computed.
"""
import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sys
sys.path.append(str(Path(__file__).resolve().parent))
import design as D
D.apply_matplotlib()
bare = D.bare
# role names kept so the chart code below reads unchanged
BLUE, RED, AQUA, GREY = D.TEAL, D.BRICK, D.AMBER, D.STONE
INK, MUTED, RULE = D.INK, D.MUTED, D.RULE
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "slides"
B = json.loads((OUT / "business_facts.json").read_text())
V = json.loads((OUT / "value_facts.json").read_text())
S = json.loads((OUT / "stats_facts.json").read_text())





# ---------------------------------------------------------------- 1. value levers
# Diverging: what adds value, what destroys it. One chart answers "where should
# a refurbishment budget go?", which is the question a valuation workflow actually has.
levers = [
    ("Add a bathroom", B["bathroom"]["usd"]),
    ("+1 condition point", B["condition"]["usd"]),
    ("+100 sqft of living space", B["sqft_100"]["usd"]),
    ("+1 view point", B["view_point"]["usd"]),
    ("100 sqft below grade\ninstead of above", B["basement_100"]["usd"]),
    ("Subdivide: +1 bedroom,\nsame floor area", B["bedroom"]["usd"]),
]
levers.sort(key=lambda t: t[1])
fig, ax = plt.subplots(figsize=(11, 4.0))
vals = [v for _, v in levers]
ax.barh([k for k, _ in levers], [v / 1000 for v in vals],
        color=[D.TEAL if v > 0 else D.BRICK for v in vals], height=0.6)
ax.axvline(0, color=GREY, lw=1)
span = max(abs(v) for v in vals) / 1000
for y, v in enumerate(vals):
    ax.text(v / 1000 + (1.6 if v > 0 else -1.6), y, f"${v/1000:+,.0f}k",
            va="center", ha="left" if v > 0 else "right", fontsize=12.5, color=INK)
ax.set_xlim(-span * 0.62, span * 1.42)
ax.set_xticks([])
ax.set_title(f"What the market pays for, on a median ${B['median_price']:,.0f} home\n"
             "— holding city and total floor area constant", fontsize=14)
bare(ax, keep=())
fig.tight_layout(); fig.savefig(OUT / "fig_value_levers.png", dpi=200); plt.close(fig)

# ---------------------------------------------------------------- 2. the money
# Three bars, one message: what the alternatives cost you per house.
fig, ax = plt.subplots(figsize=(11, 3.5))
rows = [("Zip median price\n(a lookup, no model)", V["rule_zipmed_mae"], D.STONE),
        ("Zip $/sqft x size\n(a valuation benchmark)", V["rule_ppsf_mae"], D.STONE),
        ("This model", V["mae"], D.AMBER)]
ax.barh([r[0] for r in rows], [r[1] / 1000 for r in rows],
        color=[r[2] for r in rows], height=0.6)
for y, r in enumerate(rows):
    ax.text(r[1] / 1000 + 2.5, y, f"${r[1]/1000:,.0f}k", va="center",
            fontsize=13, color=INK)
ax.set_xlim(0, max(r[1] for r in rows) / 1000 * 1.25)
ax.set_xticks([])
ax.set_title("Average error per house, on 869 sales the model never saw", fontsize=14)
bare(ax, keep=())
fig.tight_layout(); fig.savefig(OUT / "fig_money.png", dpi=200); plt.close(fig)

# ---------------------------------------------------------------- 3. confidence by segment
# A dumbbell: each segment's 10-90 band, against the global band it replaces.
bands = sorted(V["segment_bands"], key=lambda b: b["width"])
fig, ax = plt.subplots(figsize=(11, 3.9))
ys = range(len(bands))
for y, b in zip(ys, bands):
    colour = RED if b["width"] > 60 else BLUE
    ax.plot([b["lo"], b["hi"]], [y, y], color=colour, lw=9, solid_capstyle="round")
    ax.text(b["hi"] + 2, y, f"{b['width']:.0f} pp wide", va="center",
            fontsize=12, color=INK if colour == RED else MUTED)
ax.axvspan(V["global_lo"], V["global_hi"], color=D.SHADE, zorder=0)
ax.axvline(0, color=GREY, lw=1)
ax.set_yticks(list(ys))
ax.set_yticklabels([f"{b['segment']}\n{b['n']} houses" for b in bands], fontsize=11.5)
ax.set_xlabel("prediction error, %   (shaded: the single band the model used to quote)")
ax.set_xlim(-45, 75)
ax.set_title("How wrong the model can be, by segment — 8 houses in 10 land inside each bar",
             fontsize=14)
bare(ax)
fig.tight_layout(); fig.savefig(OUT / "fig_confidence_bands.png", dpi=200); plt.close(fig)

# ---------------------------------------------------------------- 4. benchmark, sourced
# Zillow's published nationwide median error rates change over time, so the figures and
# the date they were checked live in deck_facts.json, next to the URL they came from.
Z = json.loads((OUT / "deck_facts.json").read_text())["zillow"]
fig, ax = plt.subplots(figsize=(11, 3.4))
rows = [("No model: zip median", V["rule_zipmed_medape"], D.BRICK),
        ("This model", V["medape"], D.AMBER),
        ("Zestimate, off-market\n(US-wide, Zillow's figure)", Z["off_market"], D.GRAPHITE),
        ("Zestimate, on-market —\nbut it can see the asking price", Z["on_market"], D.STONE)]
ax.barh([r[0] for r in rows][::-1], [r[1] for r in rows][::-1],
        color=[r[2] for r in rows][::-1], height=0.58)
for y, r in enumerate(rows[::-1]):
    ax.text(r[1] + 0.35, y, f"{r[1]:.1f}%", va="center", fontsize=12.5, color=INK)
ax.set_xlim(0, 24)
ax.set_xlabel("median absolute percentage error")
ax.set_title(f"Where this model sits    ·    Zillow's figures checked {Z['checked']}", fontsize=14)
bare(ax)
fig.tight_layout(); fig.savefig(OUT / "fig_benchmark.png", dpi=200); plt.close(fig)

# ---------------------------------------------------------------- 5. model comparison + XGB
comp = pd.read_csv(ROOT / "Models" / "model_comparison.csv", index_col=0)
order = [m for m in ["Ridge baseline", "RF (defaults)", "GB (defaults)", "XGB (defaults)",
                     "RF (tuned)", "GB (tuned)", "XGB (tuned)"] if m in comp.index]
vals = comp.loc[order, "MedAPE_%"]
fig, ax = plt.subplots(figsize=(11, 3.8))
colours = [D.AMBER if m == "GB (tuned)" else (D.TEAL if m == "XGB (tuned)" else D.STONE)
           for m in order]
ax.bar(range(len(order)), vals, color=colours, width=0.62)
ax.set_xticks(range(len(order)))
ax.set_xticklabels([m.replace(" baseline", "") for m in order], fontsize=11)
for x, v in enumerate(vals):
    ax.text(x, v + 0.2, f"{v:.2f}%", ha="center", fontsize=12, color=INK)
ax.set_ylim(0, max(vals) * 1.25)
ax.set_ylabel("median error, %")
ax.set_title("Median percentage error on 869 unseen houses — lower is better", fontsize=14)
bare(ax)
fig.tight_layout(); fig.savefig(OUT / "fig_model_comparison.png", dpi=200); plt.close(fig)

# ---------------------------------------------------------------- 6. zip spread, thick zips
raw = pd.read_csv(ROOT / "Data" / "data_clean.csv", dtype={"zipcode": str})
ppsf = raw["price"] / raw["sqft_living"]
g = ppsf.groupby(raw["zipcode"]).agg(["median", "size"])
thick = g[g["size"] >= 30].sort_values("median")
fig, ax = plt.subplots(figsize=(11, 3.4))
ax.bar(range(len(thick)), thick["median"], color=D.AMBER, width=0.85)
ax.set_xticks([])
ax.set_xlabel(f"{len(thick)} zip codes with 30 or more sales, cheapest to dearest")
ax.set_ylabel("median $ per sqft")
ax.set_ylim(0, thick["median"].max() * 1.22)
ax.set_title(f"The same square foot costs {B['zip_ratio']:.1f}x more at one end "
             "of the county than the other", fontsize=14, pad=14)
ax.annotate(f"${thick['median'].iloc[-1]:,.0f}  {B['zip_hi_city']}",
            (len(thick) - 1, thick["median"].iloc[-1]), xytext=(-8, 5),
            textcoords="offset points", ha="right", color=INK, fontsize=12)
ax.annotate(f"${thick['median'].iloc[0]:,.0f}  {B['zip_lo_city']}",
            (0, thick["median"].iloc[0]), xytext=(8, 5),
            textcoords="offset points", color=INK, fontsize=12)
bare(ax)
fig.tight_layout(); fig.savefig(OUT / "fig_zip_spread.png", dpi=200); plt.close(fig)

# ---------------------------------------------------------------- 7. IAAO, two survivors
tab = S["iaao_notebook09"]
fig, axes = plt.subplots(1, 3, figsize=(11, 3.0))
specs = [("Median ratio", "median_ratio", 0.90, 1.10, "no systematic bias"),
         ("COD", "cod", 5, 15, "consistency"),
         ("PRD", "prd", 0.98, 1.03, "cheap vs expensive alike")]
models = ["Ridge baseline", "RF (tuned)", "GB (tuned)", "XGB (tuned)"]
marker_colour = {"GB (tuned)": D.AMBER, "XGB (tuned)": D.TEAL,
                 "RF (tuned)": D.GRAPHITE, "Ridge baseline": D.GRAPHITE}
for ax, (name, key, lo, hi, sub) in zip(axes, specs):
    span = hi - lo
    ax.axvspan(lo, hi, color=D.SHADE, zorder=0)
    for i, m in enumerate(models):
        v = tab[m][key]
        inside = lo <= v <= hi
        ax.scatter([v], [i], s=110, zorder=3, color=marker_colour[m],
                   marker="o" if inside else "X")
    ax.set_xlim(lo - 0.6 * span, hi + 0.6 * span)
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels([m.replace(" (tuned)", "").replace(" baseline", "") for m in models],
                       fontsize=10.5)
    ax.set_ylim(-0.7, len(models) - 0.3)
    ax.set_xticks([lo, hi])
    ax.set_title(name, fontsize=13, pad=8)
    ax.set_xlabel(f"target {lo}–{hi}\n{sub}", fontsize=10.5)
    bare(ax, keep=())
fig.suptitle("IAAO ratio study — a cross is a failure. Two models survive, not one.",
             y=1.04, fontsize=14)
fig.tight_layout(); fig.savefig(OUT / "fig_iaao.png", dpi=200, bbox_inches="tight"); plt.close(fig)

print("wrote:")
for f in ["fig_value_levers", "fig_money", "fig_confidence_bands", "fig_benchmark",
          "fig_model_comparison", "fig_zip_spread", "fig_iaao"]:
    print("  ", f + ".png")
