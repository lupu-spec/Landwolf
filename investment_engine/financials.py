def total_acquisition_cost(costs):
    keys = ["bid","government","liens","title","repairs","holding","auction","closing","other"]
    return sum(float(costs.get(k, 0)) for k in keys)


def profit(sale_price, selling_cost, tac):
    return float(sale_price) - float(selling_cost) - float(tac)


def roi(profit_value, cash_invested):
    if cash_invested == 0:
        return None
    return float(profit_value) / float(cash_invested)


class FinancialCalculator:
    total_acquisition_cost = staticmethod(total_acquisition_cost)
    profit = staticmethod(profit)
    roi = staticmethod(roi)
