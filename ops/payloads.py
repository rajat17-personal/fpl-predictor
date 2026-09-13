"""Pydantic schema validation for the two FPL payloads the pipeline consumes:
bootstrap-static (players/teams/events) and fixtures.

An FPL payload missing a field the pipeline subscripts directly — or one whose
`elements`/`teams`/`events` list has silently gone empty — must stop the run
before any model inference happens, with a message naming the failing field
path. `extra="ignore"` on every model means an FPL *addition* is never treated
as a failure; only a genuine required-field drift is.

Two validation profiles exist for the bootstrap because two different capture
shapes flow through the same validator: the live FPL API (profile="live")
always carries `transfers_in_event`/`transfers_out_event`, which
`predict.live._gw_pool` subscripts directly; the frozen, trimmed E2E capture
(profile="fixture") deliberately omits them (D-10/D-08 — never mutate the
frozen v1 fixture set to add fields it was never meant to carry).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from ops.jsonio import PayloadError

# Fields `predict.live._gw_pool` subscripts directly (`el["transfers_in_event"]`,
# `el["transfers_out_event"]`) that only the live FPL API payload carries — the
# trimmed E2E capture omits both, which is exactly why two profiles exist.
LIVE_ONLY_ELEMENT_FIELDS = ("transfers_in_event", "transfers_out_event")

_VALID_PROFILES = ("live", "fixture")


class Team(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    name: str
    short_name: str


class Event(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    finished: bool
    is_next: bool | None = None
    deadline_time: str | None = None


class Element(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    code: int
    web_name: str
    team: int
    element_type: int
    now_cost: int
    selected_by_percent: float
    status: str | None = None
    chance_of_playing_next_round: float | None = None

    @field_validator("element_type")
    @classmethod
    def _element_type_in_range(cls, v: int) -> int:
        if v not in (1, 2, 3, 4):
            raise ValueError("element_type must be one of 1, 2, 3, 4")
        return v


class Fixture(BaseModel):
    model_config = ConfigDict(extra="ignore")
    team_h: int
    team_a: int
    team_h_difficulty: int
    team_a_difficulty: int
    event: int | None = None
    kickoff_time: str | None = None
    finished: bool | None = None


class Bootstrap(BaseModel):
    model_config = ConfigDict(extra="ignore")
    elements: list[Element]
    teams: list[Team]
    events: list[Event]
    total_players: int

    @field_validator("elements", "teams", "events")
    @classmethod
    def _non_empty(cls, v: list, info) -> list:
        if not v:
            raise ValueError(f"{info.field_name} must not be empty")
        return v


def _format_errors(exc: ValidationError, limit: int = 3) -> str:
    parts = []
    for err in exc.errors()[:limit]:
        loc = ".".join(str(p) for p in err["loc"])
        parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts)


def validate_bootstrap(obj, *, source: str, profile: str = "live") -> Bootstrap:
    """Validate a bootstrap-static payload. Raises `PayloadError` on any
    schema violation, naming `source` and up to the first three error
    locations. `profile="live"` additionally requires every element to carry
    `LIVE_ONLY_ELEMENT_FIELDS`; `profile="fixture"` skips that extra check.
    """
    if profile not in _VALID_PROFILES:
        raise ValueError(f"unsupported profile {profile!r}; expected one of {_VALID_PROFILES}")
    try:
        model = Bootstrap.model_validate(obj)
    except ValidationError as exc:
        raise PayloadError(f"bootstrap-static payload ({source}): {_format_errors(exc)}") from exc

    if profile == "live":
        raw_elements = obj.get("elements", []) if isinstance(obj, dict) else []
        for idx, el in enumerate(raw_elements):
            for field in LIVE_ONLY_ELEMENT_FIELDS:
                if field not in el:
                    raise PayloadError(
                        f"bootstrap-static payload ({source}): elements[{idx}].{field}: "
                        "Field required for profile='live'"
                    )
    return model


def validate_fixtures(obj, *, source: str) -> list[Fixture]:
    """Validate a fixtures payload (a bare JSON list). Raises `PayloadError`
    naming `source`, the failing entry's index, and the failing field."""
    if not isinstance(obj, list):
        raise PayloadError(f"fixtures payload ({source}): expected a JSON list, got "
                          f"{type(obj).__name__}")
    fixtures = []
    for idx, entry in enumerate(obj):
        try:
            fixtures.append(Fixture.model_validate(entry))
        except ValidationError as exc:
            raise PayloadError(
                f"fixtures payload ({source}): [{idx}] {_format_errors(exc)}"
            ) from exc
    return fixtures
