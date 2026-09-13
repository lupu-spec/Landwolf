def find_max_bid(evaluator, low, high, precision=100, require_monotonicity=True):
    if low > high or precision <= 0:
        raise ValueError("Invalid bid search bounds")
    if require_monotonicity:
        if evaluator(low) is False and evaluator(high) is True:
            raise ValueError("Evaluator is non-monotonic or bounds are invalid")

    best = low if evaluator(low) else None
    lo, hi = low, high
    while hi - lo > precision:
        mid = (lo + hi) / 2
        if evaluator(mid):
            best = mid
            lo = mid
        else:
            hi = mid
    return best


class MaximumBidSearch:
    def __call__(self, evaluator, low, high, precision=100, require_monotonicity=True):
        return find_max_bid(evaluator, low, high, precision, require_monotonicity)
