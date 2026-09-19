"""Versioned extension contracts. Unimplemented services cannot advertise readiness."""

from typing import Literal, Protocol, Self

from pydantic import Field, field_validator, model_validator

from landwolf.schemas import Contract, Range


class Evidence(Contract):
    field: str
    label: str
    value: str | float | int | None
    basis: Literal["reported", "calculated", "estimated", "unknown"]
    source_url: str | None = None
    retrieved_at: str | None = None
    effective_date: str | None = None
    limitation: str = ""


class ValuationRequest(Contract):
    parcel_id: str = Field(min_length=1, max_length=64)
    strategy: Literal["vacant_land", "agriculture", "residential", "development"]


class ValuationResult(Contract):
    status: Literal["supported", "insufficient_evidence"]
    resale: Range | None = None
    comparable_ids: list[str] = Field(default_factory=list, max_length=30)
    evidence: list[Evidence] = Field(default_factory=list, max_length=100)
    limitations: list[str] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def evidence_required(self) -> Self:
        if self.status == "supported" and (
            self.resale is None or not self.comparable_ids or not self.evidence
        ):
            raise ValueError("Supported valuations require a range, comparables and evidence")
        if self.status == "insufficient_evidence" and self.resale is not None:
            raise ValueError("Do not publish a valuation when evidence is insufficient")
        return self


class ValuationProvider(Protocol):
    async def evaluate(self, request: ValuationRequest) -> ValuationResult: ...


class PartnerConsent(Contract):
    """Future inquiries require explicit recipients, fields, and current consent."""

    recipient_ids: list[str] = Field(min_length=1, max_length=3)
    shared_fields: list[Literal["email", "property", "scenario"]] = Field(
        min_length=1, max_length=3
    )
    disclosure_version: str = Field(min_length=1, max_length=40)
    consent: Literal[True]

    @field_validator("consent", mode="before")
    @classmethod
    def explicit_consent(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Explicit boolean consent is required")
        return value


class PartnerGateway(Protocol):
    async def submit(self, account_id: str, consent: PartnerConsent) -> str: ...


class SourceReadiness(Contract):
    """New adapters need evidence for each gate before a future rollout."""

    source_id: str
    parser_tests_passed: bool = False
    live_check_passed: bool = False
    reuse_reviewed: bool = False
    freshness_monitored: bool = False

    @property
    def eligible(self) -> bool:
        return all(
            (
                self.parser_tests_passed,
                self.live_check_passed,
                self.reuse_reviewed,
                self.freshness_monitored,
            )
        )


def capabilities() -> list[dict[str, object]]:
    return [
        {
            "priority": 1,
            "id": "trust",
            "name": "Trust and usability",
            "status": "beta",
            "description": "Evidence, research summary, source monitoring and account recovery.",
        },
        {
            "priority": 2,
            "id": "decisions",
            "name": "Decision quality",
            "status": "framework",
            "description": "Comparable-sale valuation and parcel-wide analysis are not enabled.",
        },
        {
            "priority": 3,
            "id": "partners",
            "name": "Partner pilot",
            "status": "framework",
            "description": "Consent contracts defined. Advertising and data sharing are disabled.",
        },
        {
            "priority": 4,
            "id": "expansion",
            "name": "Coverage expansion",
            "status": "framework",
            "description": "Onboarding gates defined. Only listed feeds supply records.",
        },
    ]
