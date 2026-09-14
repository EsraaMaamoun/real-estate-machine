- **The notebook's story, as the user distilled it:**
  ```
  LOG PRICE
     |
  Linear / Ridge / Lasso
     |
  Cross-validation
     |
  Choose Ridge systematically (one-SE rule)
     |
  Evaluate
     |
  Residual diagnostics
     |
  Discover systematic error patterns (over-values cheap, under-values expensive)
     |
  Check error by market segment
     |
  Premium properties ~= 2x harder
     |
  Compare with real-world benchmarks (Zestimate, institutional AVM)
     |
  IAAO ratio study:
    Level       PASS
    Vertical    PASS
    Uniformity  FAIL (narrow)
     |
  FINAL BUSINESS DECISION
     |
  Useful screening / triage tool, NOT a formal valuation system
  ```
- **Findings from the review:**
  1. `segment_test` (cell after setup) reads `data_clustered.csv` fresh and lines it up with
     `is_test` **by position**, with no assertion that it shares row order/count with
     `data_clean.csv`. Verified it currently does align (4,345 rows, byte-identical on
     `price`/`sqft_living`/`zipcode`), but nothing guards against this silently breaking if
     `data_clustered.csv` is ever regenerated out of order — recommended an `assert`.
  2. The Duan-smearing decision (Section 3) is tested on a `probe` Ridge (alpha=1.0), not on
     the tuned Ridge (alpha=100) that actually ships. Low risk — Section 5 shows alpha barely
     moves the score — but not literally re-verified on the shipped model.
  3. The Section 11 "honest range" for a single house uses one global 10th/90th-percentile
     spread across the whole test set, even though Sections 8–9 prove the error is segment-
     and price-dependent. Worth conditioning on price decile or segment if this range is what
     the Streamlit app shows end users.
- Everything else checked out clean: metric choices, IAAO COD/PRD formulas (textbook-correct
  for the log1p target), confidence-interval bound ordering, leakage-safety of the zip-code
  baseline.

