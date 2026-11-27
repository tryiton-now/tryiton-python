"""Official Python SDK for the TryItOn virtual try-on API.

See https://docs.tryiton.now for the full API reference.
"""

from .client import (
    TryItOn,
    TryItOnError,
    HAIRCUTS,
)
from .types import (
    Status,
    Credits,
    LiveConfig,
    LiveGarment,
    LiveGarmentInput,
    LiveSessionGarment,
    LiveConnection,
    LiveSession,
    LiveSessionStart,
)

__all__ = [
    "TryItOn",
    "TryItOnError",
    "HAIRCUTS",
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
# Single source of the SDK version (sent in the User-Agent); keep it equal to pyproject.toml.
__version__ = "2.2.0"
