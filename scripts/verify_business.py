"""
verify_business.py — recompute every business number that goes on a slide.

Nothing here is copied from the business report. Each figure is recomputed
from Data/data_clean.csv so the deck and the report can be checked against each
other, and so any number quoted in the defence has been produced by a run.

Writes reports/slides/business_facts.json.
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "app"))
import preprocessing as P  # noqa: E402

raw = pd.read_csv(ROOT / "Data" / "data_clean.csv", dtype={"zipcode": str})
df = P.engineer_features(raw)
F = {}

median_price = float(df["price"].median())
F["median_price"] = median_price
F["n"] = len(df)

# ---------------------------------------------------------------------------
# 1. Location spread.
#
# The business report quoted 3.2x; the deck's chart quoted 4.2x. Both are right for
# different zip sets: the extremes of the full 77 include zips with a handful of
# sales. A minimum of 30 sales is the defensible cut, and it is used everywhere
# from here on, so the chart and the business slide cannot disagree.
# ---------------------------------------------------------------------------
ppsf = df["price"] / df["sqft_living"]
by_zip = ppsf.groupby(df["zipcode"]).agg(["median", "size"])
thick = by_zip[by_zip["size"] >= 30].sort_values("median")

F["zip_all_n"] = int(len(by_zip))
F["zip_thick_n"] = int(len(thick))
F["zip_lo"] = float(thick["median"].iloc[0])
F["zip_hi"] = float(thick["median"].iloc[-1])
F["zip_ratio"] = F["zip_hi"] / F["zip_lo"]
F["zip_lo_name"] = str(thick.index[0])
F["zip_hi_name"] = str(thick.index[-1])
# the same house, priced in each
F["same_house_sqft"] = 2000
F["same_house_lo"] = F["zip_lo"] * 2000
F["same_house_hi"] = F["zip_hi"] * 2000

city_of = df.groupby("zipcode")["city"].agg(lambda s: s.mode().iat[0])
F["zip_lo_city"] = str(city_of[F["zip_lo_name"]])
F["zip_hi_city"] = str(city_of[F["zip_hi_name"]])

# ---------------------------------------------------------------------------
# 2. What each feature is worth, holding city and floor area constant.
#
# log(price) on the structural features plus city dummies. The coefficient on a
# feature is its proportional effect; exp(b) - 1 converts it to a percentage, and
# multiplying by the median price puts it in dollars. City dummies are what makes
# this "holding location constant" — without them every coefficient is really
# measuring where the house is.
# ---------------------------------------------------------------------------
feat = ["sqft_living", "bathrooms", "bedrooms", "sqft_basement",
        "condition", "view", "house_age", "floors"]
X = pd.concat([df[feat], pd.get_dummies(df["city"], prefix="city", drop_first=True)], axis=1)
y = np.log(df["price"])
lin = LinearRegression().fit(X, y)
coef = pd.Series(lin.coef_, index=X.columns)
F["ols_r2"] = float(lin.score(X, y))

def pct_dollars(name, unit=1.0):
    b = float(coef[name]) * unit
    pct = 100 * (np.exp(b) - 1)
    return {"pct": pct, "usd": median_price * (np.exp(b) - 1)}

F["bathroom"] = pct_dollars("bathrooms")
F["bedroom"] = pct_dollars("bedrooms")
F["condition"] = pct_dollars("condition")
F["view_point"] = pct_dollars("view")
F["basement_100"] = pct_dollars("sqft_basement", 100)
F["age_year"] = pct_dollars("house_age")
F["sqft_100"] = pct_dollars("sqft_living", 100)

# ---------------------------------------------------------------------------
# 3. Renovation: the raw gap, and the like-for-like gap inside one zip code.
# ---------------------------------------------------------------------------
ren = df["was_renovated"] == 1
F["n_renovated"] = int(ren.sum())
F["reno_raw_pct"] = float(100 * (ppsf[ren].median() / ppsf[~ren].median() - 1))
F["reno_age_renovated"] = float(df.loc[ren, "house_age"].median())
F["reno_age_not"] = float(df.loc[~ren, "house_age"].median())

within = []
for z, g in df.groupby("zipcode"):
    a, b = g[g["was_renovated"] == 1], g[g["was_renovated"] == 0]
    if len(a) >= 5 and len(b) >= 5:
        ra = (a["price"] / a["sqft_living"]).median()
        rb = (b["price"] / b["sqft_living"]).median()
        within.append(100 * (ra / rb - 1))
F["reno_within_zips"] = len(within)
F["reno_within_median_pct"] = float(np.median(within))
F["reno_within_negative"] = int(sum(1 for v in within if v < 0))
F["reno_breakeven_usd"] = median_price * F["reno_within_median_pct"] / 100

# ---------------------------------------------------------------------------
# 4. Where the volume is, and where the margin is.
# ---------------------------------------------------------------------------
bands = [(0, 350_000, "Entry, under $350k"),
         (350_000, 650_000, "Mid, $350-650k"),
         (650_000, 1_200_000, "Upper, $650k-1.2m"),
         (1_200_000, np.inf, "Luxury, above $1.2m")]
seg_rows = []
for lo, hi, name in bands:
    m = (df["price"] >= lo) & (df["price"] < hi)
    seg_rows.append({"band": name, "n": int(m.sum()),
                     "share": float(100 * m.mean()),
                     "ppsf": float(ppsf[m].median()),
                     "sqft": float(df.loc[m, "sqft_living"].median())})
F["price_bands"] = seg_rows
F["share_under_650k"] = float(100 * (df["price"] < 650_000).mean())
F["ppsf_ratio_lux_entry"] = seg_rows[-1]["ppsf"] / seg_rows[0]["ppsf"]

# ---------------------------------------------------------------------------
# 5. Sample-size caveats that belong on the slide, not in a footnote.
# ---------------------------------------------------------------------------
F["n_waterfront"] = int(df["waterfront"].sum())
F["n_view_positive"] = int((df["view"] > 0).sum())
F["waterfront_median"] = float(df.loc[df["waterfront"] == 1, "price"].median())
F["nonwaterfront_median"] = float(df.loc[df["waterfront"] == 0, "price"].median())

out = ROOT / "reports" / "slides" / "business_facts.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(F, indent=1, default=float))

print(f"n = {F['n']:,}   median price ${median_price:,.0f}   OLS R2 = {F['ols_r2']:.3f}\n")
print(f"LOCATION  ({F['zip_thick_n']} zips with 30+ sales, of {F['zip_all_n']})")
print(f"  ${F['zip_lo']:.0f}/sqft ({F['zip_lo_city']} {F['zip_lo_name']}) "
      f"-> ${F['zip_hi']:.0f}/sqft ({F['zip_hi_city']} {F['zip_hi_name']})  = {F['zip_ratio']:.1f}x")
print(f"  a 2,000 sqft house: ${F['same_house_lo']:,.0f} vs ${F['same_house_hi']:,.0f}\n")
print("VALUE LEVERS (city and floor area held constant)")
for k in ["bathroom", "bedroom", "condition", "view_point", "basement_100", "age_year", "sqft_100"]:
    print(f"  {k:14s} {F[k]['pct']:+6.1f}%   ${F[k]['usd']:+,.0f} on a median home")
print(f"\nRENOVATION  raw +{F['reno_raw_pct']:.0f}%  -> like-for-like "
      f"{F['reno_within_median_pct']:+.0f}% across {F['reno_within_zips']} zips "
      f"({F['reno_within_negative']} negative)")
print(f"  median age renovated {F['reno_age_renovated']:.0f} vs unrenovated {F['reno_age_not']:.0f} years")
print(f"  break-even budget ${F['reno_breakeven_usd']:,.0f}\n")
print(f"VOLUME  {F['share_under_650k']:.0f}% of sales under $650k; "
      f"luxury $/sqft is {F['ppsf_ratio_lux_entry']:.1f}x entry")
for r in seg_rows:
    print(f"  {r['band']:22s} {r['n']:5,}  {r['share']:4.0f}%  ${r['ppsf']:.0f}/sqft")
print(f"\nSAMPLES  waterfront {F['n_waterfront']}   view>0 {F['n_view_positive']}")
