# Scenario model beta-1.0

This is an illustrative planning model, not an appraisal, lien opinion, property
quality rating, or recommendation to bid. Resale and repair assumptions belong to
the user. Estimates can be wrong even if every calculation is correct.

## Editable starting assumptions

The owner-selected resale defaults are `low = bid × 0.95`, `likely = bid`, and
`high = bid × 1.20`, rounded to cents. They are hypothetical bounds, not a market
valuation or calibrated confidence interval. The current purchase/bid input is
the anchor, initially the source's published price/bid where available. Missing
prices require an entered bid or explicit resale assumptions. Percentages are
editable; user-edited dollar fields stop tracking the anchor until explicitly reset.

Unestimated costs and holding period default to zero by owner request. This excludes
expenses and may overstate profits and maximum bid. The browser requires an explicit
acknowledgment whenever a cost or holding period is zero; API output independently
warns about zero inputs. API clients retain responsibility for reviewing assumptions.
ROI/profit/loss targets are preferences, not property statistics.

No calibrated comparable-cost dataset is connected. Assessments, taxes owed, and
asking prices are not substitutes for market value, annual taxes, or surviving liens.
The fallback is a labeled zero placeholder, not an invented statistical estimate.
An evidence-based extension would require dated, attributable observations matched
by property/use and region, with sample counts and a documented county-to-region
fallback; this patch does not claim that data or an estimator is connected.

## Simulation

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
