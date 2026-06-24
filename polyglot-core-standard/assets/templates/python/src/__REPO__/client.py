"""The Python boundary wrapper — the analog of Swift's `CoreClient`.

ALL core calls go through here. The hand-written PyO3 layer (governed core code in
`core/crates/__REPO__-py`) returns plain Python values; this module PARSES them into a
pydantic v2 model at the boundary (parse, don't validate — non-negotiable 3). A core failure
surfaces as a `PyErr` and is re-typed into a host-domain exception here.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from __REPO__ import _native


class Totp(BaseModel):
    """Host-native, validated view of the core's TOTP contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    secret: str = Field(min_length=1)
    digits: int = Field(ge=4, le=10)
    period: int = Field(gt=0)
    algorithm: str


class CoreClientError(Exception):
    """A core failure re-typed into the host's own domain at the boundary."""


def parse_otpauth(uri: str) -> Totp:
    """Call the native core, then re-type the result into a validated pydantic model."""
    try:
        raw = _native.parse_otpauth(uri)
    except ValueError as exc:  # CoreError -> PyErr (never a panic / interpreter abort)
        raise CoreClientError(str(exc)) from exc
    return Totp.model_validate(raw)
