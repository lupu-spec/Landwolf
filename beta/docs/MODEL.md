# Scenario model beta-1.0

This is an illustrative planning model, not an appraisal, lien opinion, property
quality rating, or recommendation to bid. Resale and repair assumptions belong to
the user. Estimates can be wrong even if every calculation is correct.

For each seeded simulation:

```text
sale = triangular(resale low, likely, high)
repairs = triangular(repair low, likely, high)
fixed = lien reserve + closing costs + months × monthly holding
bid multiplier = 1 + buyer premium / 100 + APR / 100 × months / 12
investment = repairs + fixed + bid × bid multiplier
proceeds = sale × (1 − selling costs / 100)
profit = proceeds − investment
ROI = profit / investment
```

Equal endpoints give a fixed value. Values must be finite, nonnegative, bounded,
and ordered. Resale must be positive. Financing charges simple interest on 100%
of the bid, with no amortization or compounding. Taxes, insurance and maintenance
belong in monthly holding costs. Loan structure and cash-on-cash returns are not
modeled. The displayed ROI uses modeled total investment, including the bid.

The maximum-bid search uses 48 bisection steps and rounds down to cents. A bid
qualifies when sampled loss probability is at most the chosen limit, median profit
is at least the chosen minimum, and median ROI reaches the chosen target. Fixed
draws preserve the monotonic relationship between bid and all three gates. A
zero-investment positive-proceeds scenario satisfies the return constraint but
has no finite displayed ROI or score. An infeasible result is null, not a zero bid.

Scenario score is `100 × (1 − loss probability) × ROI attainment`, with attainment
clamped to [0, 1] and the target denominator bounded below at 1%. It measures fit
to the entered return target, not title quality, investment safety or likelihood
that the assumptions are true. A score cannot clear an unresolved diligence item.

P10/P50/P90 describe sampled profit, not guaranteed bounds. The 95% Wilson interval
describes simulation sampling error in loss probability, not market or model
uncertainty. Repair and resale draws are independent. Correlation, unknown lien
survival, changing holding periods, illiquidity, flood, market regime shifts and
seller acceptance are not estimated. Inspect legal records and sale terms before
using any output in a real transaction.

Tests cover exact fixed-case arithmetic, repeatability, cost monotonicity,
maximum-bid feasibility and boundary, invalid/nonfinite input, zero investment,
infeasible bids, and histogram totals.
