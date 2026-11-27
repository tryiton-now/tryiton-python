"""Response types for the TryItOn API client.

`Status` and `Credits` are dataclasses (attribute access, as since 0.1.0). The live
try-on responses are `TypedDict`s: plain dicts at runtime, typed for checkers. They
mirror the backend's JSON (camelCase keys) and may gain keys in later API versions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, TypedDict


@dataclass
class Status:
    """A job's status snapshot, from ``GET /status/{id}``."""

    status: str  # "processing" | "completed" | "failed"
    output: List[str]
    # The failure reason of a failed job, as plain text; None otherwise.
    error: Optional[str]


@dataclass
class Credits:
    """Your credit balance, from ``GET /credits``."""

    on_demand: int
    subscription: int
    purchased: int
    reserved: int


class LiveConfig(TypedDict):
    """Live try-on availability and pricing, from ``GET /live/config``."""

    enabled: bool
    secondsPerCredit: int
    maxSeconds: int
    minCredits: int
    maxConcurrentSessions: int


class LiveGarment(TypedDict):
    """A garment (or outfit) prepared for live try-on."""

    id: str
    category: str  # the item's category, or "outfit" for a prepare_live_outfit result
    subcategory: Optional[str]
    description: Optional[str]
    prompt: str  # the prompt the stream uses
    enhancePrompt: bool  # whether the stream rewrites `prompt`
    items: Optional[List[str]]  # an outfit's garment ids, top to bottom; None for a single garment
    createdAt: str  # ISO 8601


class LiveGarmentInput(TypedDict):
    """The stream input for a prepared garment."""

    prompt: str
    enhancePrompt: bool
    referenceImage: str  # data URL


class LiveSessionGarment(LiveGarment):
    """The starting garment of a live session, with its stream input."""

    input: Optional[LiveGarmentInput]


class LiveConnection(TypedDict):
    """Media-provider connection details for the end user's browser."""

    provider: str
    model: str
    token: str


class LiveSession(TypedDict):
    """A live session's status and usage."""

    id: str
    status: str  # "active" | "ended"
    endReason: Optional[str]
    seconds: int
    creditsCharged: int
    endUserId: Optional[str]
    createdAt: str  # ISO 8601
    endedAt: Optional[str]


class LiveSessionStart(TypedDict):
    """The full ``POST /live/sessions`` response. Send it to the browser unchanged."""

    ok: bool
    session: LiveSession
    clientSecret: str
    connection: LiveConnection
    secondsPerCredit: int
    maxSeconds: int
    secondsLeft: int
    garment: Optional[LiveSessionGarment]


__all__ = [
    "Status",
    "Credits",
    "LiveConfig",
    "LiveGarment",
    "LiveGarmentInput",
    "LiveSessionGarment",
    "LiveConnection",
    "LiveSession",
    "LiveSessionStart",
]
