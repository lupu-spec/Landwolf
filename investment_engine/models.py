from dataclasses import dataclass, field
from typing import Any


@dataclass
class PropertyModel:
    property_id: str
    acquisition: dict
    government_costs: list[dict] = field(default_factory=list)
    liens: list[dict] = field(default_factory=list)
    title_costs: dict = field(default_factory=dict)
    repairs: list[dict] = field(default_factory=list)
    holding_period: dict = field(default_factory=dict)
    holding_costs: dict = field(default_factory=dict)
    auction_costs: dict = field(default_factory=dict)
    closing_costs: Any = 0
    other_costs: Any = 0
    valuation: dict = field(default_factory=dict)
    market_growth: dict = field(default_factory=dict)
    selling_costs: dict = field(default_factory=dict)
    inspection_quality: float = 1.0
    metadata: dict = field(default_factory=dict)
