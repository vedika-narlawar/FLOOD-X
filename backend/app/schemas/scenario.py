from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ScenarioRequest(BaseModel):
    """Hypothetical scenario. Only parameters with a documented mathematical relationship to the
    screening index are applied; the rainfall fields are accepted for record-keeping but are NOT
    applied because the static index contains no rainfall-runoff relationship."""
    name: str = Field("scenario", max_length=80)
    rainfall_multiplier: float = Field(1.0, ge=0.5, le=3.0, description="Recorded only; not applied to scores.")
    window_hours: Literal[1, 3, 6, 12, 24, 72] = 24
    weights: dict[str, float] | None = Field(None, description="Override index weights (variable name -> weight >= 0).")
    top_n: int = Field(10, ge=1, le=60)

    @field_validator("weights")
    @classmethod
    def _w(cls, v):
        if v is None:
            return v
        if len(v) > 20:
            raise ValueError("too many weight overrides")
        for k, x in v.items():
            if not (0 <= x <= 1):
                raise ValueError(f"weight for {k} must be within [0, 1]")
        return v
