"""Bounded, deterministic research decisions. No enrichment or model requests."""

from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal, Self

from pydantic import Field, field_validator, model_validator

from landwolf.schemas import Contract, PropertyRecord

Topic = Literal["access", "use", "title", "water", "septic", "power", "flood"]
TOPICS: dict[str, tuple[str, str]] = {
    "access": ("Legal access", "Which recorded document establishes access for this parcel?"),
    "use": ("Permitted use", "Is the intended use allowed here, and what approvals apply?"),
    "title": ("Title and sale terms", "Which liens, restrictions and sale obligations remain?"),
    "water": ("Water", "What water service or rights are confirmed for this parcel?"),
    "septic": ("Wastewater", "What site testing and wastewater approvals are required?"),
    "power": ("Power", "Can the provider serve this parcel, at what cost and on what timeline?"),
    "flood": ("Flood and site conditions", "What parcel-specific hazard review is still required?"),
}
MAX_CASES = 50
MAX_HISTORY = 20


def default_requirements() -> list[Topic]:
    return ["access", "use", "title"]


class Goal(Contract):
    intended_use: Literal["home", "recreation", "agriculture", "investment", "other"] = "home"
    use_details: str = Field(default="", max_length=160)
    budget: float | None = Field(default=None, gt=0, le=1_000_000_000)
    requirements: list[Topic] = Field(default_factory=default_requirements)
    max_months: int | None = Field(default=None, ge=0, le=120)

    @field_validator("requirements")
    @classmethod
    def unique_requirements(cls, value: list[Topic]) -> list[Topic]:
        if len(value) > len(TOPICS) or len(set(value)) != len(value):
            raise ValueError("Choose each requirement once")
        return value


class Evidence(Contract):
    topic: Topic
    status: Literal["unknown", "confirmed", "failed", "not_applicable"] = "unknown"
    note: str = Field(default="", max_length=500)
    source_ref: str = Field(default="", max_length=500)
    checked_on: date | None = None
    scope: Literal["this_property", "general_rule"] = "this_property"
    applicability_confirmed: bool = False

    @model_validator(mode="after")
    def supported(self) -> Self:
        if self.checked_on and self.checked_on > datetime.now(UTC).date():
            raise ValueError("Evidence date cannot be in the future")
        if self.status != "unknown" and (
            not self.note.strip() or not self.source_ref.strip() or not self.checked_on
        ):
            raise ValueError("An answer requires a note, source reference and checked date")
        if (
            self.status != "unknown"
            and self.scope == "general_rule"
            and (self.topic != "use" or not self.applicability_confirmed)
        ):
            raise ValueError(
                "General rules require permitted-use scope and confirmed applicability"
            )
        return self


class Costs(Contract):
    purchase_basis: Literal["published", "entered"] = "published"
    purchase_price: float | None = Field(default=None, ge=0, le=1_000_000_000)
    known_costs: float | None = Field(default=None, ge=0, le=1_000_000_000)
    unresolved_low: float | None = Field(default=None, ge=0, le=1_000_000_000)
    unresolved_high: float | None = Field(default=None, ge=0, le=1_000_000_000)
    net_proceeds: float | None = Field(default=None, gt=0, le=1_000_000_000)
    target_return_pct: float = Field(default=20, ge=0, le=1000)
    holding_months: int | None = Field(default=None, ge=0, le=120)
    monthly_holding: float | None = Field(default=None, ge=0, le=1_000_000)
    extra_cost: float = Field(default=0, ge=0, le=1_000_000_000)
    delay_months: int = Field(default=0, ge=0, le=120)

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.purchase_basis == "entered" and self.purchase_price is None:
            raise ValueError("Enter an acquisition assumption")
        if self.purchase_basis == "published" and self.purchase_price is not None:
            raise ValueError("Published price cannot also have a manual override")
        if (self.unresolved_low is None) != (self.unresolved_high is None):
            raise ValueError("Provide both ends of the unresolved-cost range")
        if (
            self.unresolved_low is not None
            and self.unresolved_high is not None
            and self.unresolved_low > self.unresolved_high
        ):
            raise ValueError("Cost range is reversed")
        if self.delay_months and self.monthly_holding is None:
            raise ValueError("A delay scenario needs monthly carrying cost")
        return self


class CaseInput(Contract):
    revision: int = Field(default=0, ge=0)
    hunt_id: str | None = Field(default=None, min_length=1, max_length=36)
    goal: Goal = Field(default_factory=Goal)
    costs: Costs = Field(default_factory=Costs)
    evidence: list[Evidence] = Field(default_factory=list, max_length=len(TOPICS))
    authority: str = Field(default="", max_length=160)
    authority_confirmed: bool = False
    pause_reason: Literal["", "budget", "access", "use", "power", "timeline", "other"] = ""
    pause_note: str = Field(default="", max_length=400)

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if len({item.topic for item in self.evidence}) != len(self.evidence):
            raise ValueError("Each research topic must be unique")
        if self.authority_confirmed and not self.authority.strip():
            raise ValueError("Name the confirmed planning authority")
        if self.pause_reason == "other" and not self.pause_note.strip():
            raise ValueError("Explain the reason to pause")
        return self


class GoalInput(Contract):
    revision: int = Field(default=0, ge=0)
    goal: Goal


class CompareInput(Contract):
    listing_ids: list[str] = Field(min_length=2, max_length=2)

    @field_validator("listing_ids")
    @classmethod
    def distinct(cls, value: list[str]) -> list[str]:
        if len(set(value)) != 2 or any(not 1 <= len(v) <= 80 for v in value):
            raise ValueError("Choose two different properties")
        return value


def amount(value: Decimal | None) -> float | None:
    return None if value is None else float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def decimal(value: float | int) -> Decimal:
    return Decimal(str(value))


def economics(spec: Costs, goal: Goal, record: PropertyRecord) -> dict[str, Any]:
    """Known costs include base holding; stress adds only incremental delay/cost."""
    price = record.asking_price if spec.purchase_basis == "published" else spec.purchase_price
    warnings = [
        "Customer assumptions, not a valuation. Known additional costs must include closing, "
        "base holding, financing and other accounted-for costs; exclude unresolved work.",
        "Net proceeds must already deduct selling expenses. "
        "Return is total-period, not annualized.",
    ]
    if spec.purchase_basis == "published":
        warnings.append(
            f"Acquisition uses {record.price_kind.lower()}; it is not a final sale price."
        )
    if spec.known_costs == 0:
        warnings.append("Zero additional costs are your assumption and can overstate headroom.")
    known = (
        decimal(price) + decimal(spec.known_costs)
        if price is not None and spec.known_costs is not None
        else None
    )
    budget = decimal(goal.budget) if goal.budget is not None else None
    return_limit = (
        decimal(spec.net_proceeds) / (1 + decimal(spec.target_return_pct) / 100)
        if spec.net_proceeds is not None
        else None
    )
    limits = [v for v in (budget, return_limit) if v is not None]
    limit = min(limits) if limits else None
    headroom = limit - known if limit is not None and known is not None else None
    stress = decimal(spec.extra_cost) + decimal(spec.delay_months) * decimal(
        spec.monthly_holding or 0
    )
    low = (
        known + decimal(spec.unresolved_low)
        if known is not None and spec.unresolved_low is not None
        else None
    )
    high = (
        known + decimal(spec.unresolved_high) + stress
        if known is not None and spec.unresolved_high is not None
        else None
    )
    status = "incomplete"
    if limit is not None and low is not None and high is not None:
        status = (
            "within_assumptions"
            if high <= limit
            else "exceeds_target"
            if low > limit
            else "sensitive"
        )
    roi = (
        (decimal(spec.net_proceeds) / high - 1) * 100
        if high is not None and high > 0 and spec.net_proceeds
        else None
    )
    return {
        "purchase_price": price,
        "known_total": amount(known),
        "allowance": amount(headroom),
        "budget_allowance": amount(budget - known)
        if budget is not None and known is not None
        else None,
        "return_allowance": amount(return_limit - known)
        if return_limit is not None and known is not None
        else None,
        "favorable_total": amount(low),
        "adverse_total": amount(high),
        "stress_added": amount(stress),
        "adverse_return_pct": amount(roi),
        "status": status,
        "warnings": warnings,
    }


def evaluate(
    spec: CaseInput, goal: Goal, record: PropertyRecord, *, available: bool
) -> dict[str, Any]:
    facts: dict[str, Evidence] = {e.topic: e for e in spec.evidence}
    costs = economics(spec.costs, goal, record)
    blockers = []
    questions: list[dict[str, str]] = []
    for topic, (label, question) in TOPICS.items():
        fact = facts.get(topic)
        status = fact.status if fact else "unknown"
        required = topic in goal.requirements
        if required and status != "confirmed":
            blockers.append(
                f"{label}: {'requirement not met' if status == 'failed' else 'needs verification'}"
            )
        if status == "confirmed" or (status == "not_applicable" and not required):
            continue
        priority = "Requirement" if required else "Follow-up"
        questions.append(
            {
                "topic": topic,
                "label": label,
                "question": question,
                "priority": priority,
                "reason": "Your requirement is not yet supported by a confirmed answer."
                if required
                else "Resolve if relevant to your intended use.",
            }
        )
    questions.sort(key=lambda q: q["priority"] != "Requirement")
    allowance = costs["allowance"]
    cost_question = {
        "topic": "costs",
        "label": "Unresolved project costs",
        "priority": "Budget",
        "question": "What do the remaining work and connection quotes total?",
        "reason": (
            f"Your remaining allowance is ${allowance:,.2f} under the entered targets."
            if allowance is not None
            else (
                "Enter acquisition, known additional costs and a budget or return "
                "scenario to calculate the threshold."
            )
        ),
    }
    if costs["status"] != "within_assumptions":
        questions.insert(sum(q["priority"] == "Requirement" for q in questions), cost_question)
    if not available:
        blockers.insert(
            0, "Listing availability needs confirmation; retained evidence is not a current offer."
        )
    pause_met: bool | None = None
    if available:
        if spec.pause_reason == "budget":
            pause_met = (
                costs["status"] == "within_assumptions" if costs["status"] != "incomplete" else None
            )
        elif spec.pause_reason in {"access", "use", "power"}:
            fact = facts.get(spec.pause_reason)
            pause_met = fact.status == "confirmed" if fact and fact.status != "unknown" else None
        elif (
            spec.pause_reason == "timeline"
            and goal.max_months is not None
            and spec.costs.holding_months is not None
        ):
            pause_met = spec.costs.holding_months + spec.costs.delay_months <= goal.max_months
    return {
        "costs": costs,
        "blockers": blockers,
        "questions": questions,
        "pause_condition_met": pause_met,
        "summary": "Requirements still need attention."
        if blockers
        else "Your recorded requirements are answered; review the underlying evidence.",
        "limitation": (
            "Answers are recorded by you, not independently certified by LandWolf. "
            "A point lookup cannot clear the whole parcel. "
            "No automatic purchase recommendation."
        ),
    }


def comparison(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Compare two explicit cases, without treating unknowns as favorable facts."""
    a, b = left["decision"]["costs"], right["decision"]["costs"]
    same_goal = left["effective_goal"] == right["effective_goal"]
    delta = (
        amount(decimal(b["known_total"]) - decimal(a["known_total"]))
        if a["known_total"] is not None and b["known_total"] is not None
        else None
    )
    message = "Enter acquisition and known additional costs for both properties."
    if delta is not None:
        message = (
            f"Total costs tie when A's remaining work and added delay costs "
            f"exceed B's by ${delta:,.2f}."
            if delta >= 0
            else (
                f"Total costs tie when B's remaining work and added delay costs "
                f"exceed A's by ${-delta:,.2f}."
            )
        )
        message += (
            " With equal known costs, lower remaining costs decide the lower total."
            if delta == 0
            else " Below that threshold, the property with lower known cost stays less expensive."
        )
    robust = None
    if same_goal and all(
        v is not None
        for v in (
            a["favorable_total"],
            a["adverse_total"],
            b["favorable_total"],
            b["adverse_total"],
        )
    ):
        if a["adverse_total"] < b["favorable_total"]:
            robust = "A costs less across the entered ranges."
        elif b["adverse_total"] < a["favorable_total"]:
            robust = "B costs less across the entered ranges."
        else:
            robust = "The cost ranges overlap; quotes or timing could change the preference."
    return {
        "a": left,
        "b": right,
        "same_goal": same_goal,
        "cost_difference": delta,
        "explanation": message,
        "range_result": robust,
        "limitation": (
            "This compares cost, not value or overall quality. Different proceeds or uses "
            "can change the decision. Unresolved requirements remain blockers; "
            "ranges are not forecasts."
        ),
    }
