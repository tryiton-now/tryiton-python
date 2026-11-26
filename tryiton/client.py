"""TryItOn API client."""

from __future__ import annotations

import time
import warnings
from typing import Any, Dict, List, Optional, cast
from urllib.parse import quote

import requests

from .types import Credits, LiveConfig, LiveGarment, LiveSession, LiveSessionStart, Status

DEFAULT_BASE_URL = "https://tryiton.now/api/v1"

# Supported `haircut` values for hairstyle try-on.
HAIRCUTS = [
    "Afro", "BobCut", "BowlCut", "BoxBraids", "BuzzCut", "Chignon", "CombOver",
    "CornrowBraids", "CurlyBob", "CurlyShag", "DoubleBun", "Dreadlocks", "FauxHawk",
    "FishtailBraid", "LongCurly", "LongHairTiedUp", "LongHimeCut", "LongStraight",
    "LongTwintails", "LongWavy", "LongWavyCurtainBangs", "ManBun", "MessyTousled",
    "PixieCut", "Pompadour", "Ponytail", "ShortCurlyPixie", "ShortTwintails",
    "ShoulderLengthHair", "Spiky", "TexturedFringe", "TwinBraids", "Updo", "WavyShag",
]


class TryItOnError(Exception):
    """Raised for API-level errors and runtime (job) failures.

    Attributes:
        status: HTTP status code, or None for a runtime job failure.
        error_name: The API error name, e.g. "OutOfCredits" or "ProcessingError".
    """

    def __init__(self, message: str, *, status: Optional[int] = None, error_name: Optional[str] = None):
        super().__init__(message)
        self.status = status
        self.error_name = error_name


class TryItOn:
    """Client for the TryItOn virtual try-on API.

    Example:
        client = TryItOn(api_key="...")
        job_id = client.try_on_fashion(
            model_image="https://example.com/model.jpg",
            garment_image="https://example.com/tshirt.jpg",
            category="clothing",
            subcategory="tops",
        )
        urls = client.wait_for_result(job_id)
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
        session: Optional[requests.Session] = None,
    ):
        if not api_key:
            raise TryItOnError("An api_key is required.", error_name="ConfigError")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()
        # Imported here, not at module level: the package __init__ imports this module first.
        from . import __version__

        self._user_agent = f"tryiton-python/{__version__}"

    def try_on_fashion(
        self,
        *,
        model_image: str,
        garment_image: str,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        mode: Optional[str] = None,
        num_samples: Optional[int] = None,
        output_format: Optional[str] = None,
        moderation_level: Optional[str] = None,
    ) -> str:
        """Put a garment or accessory on a person. Returns the job id.

        `category` is one of auto | clothing | eyewear | footwear | headwear |
        jewelry | accessories | others. `clothing`, `jewelry`, and `accessories`
        require a `subcategory`. `num_samples` is 1-4 (charged per image),
        and `output_format` is "png" or "jpeg".

        Deprecated: `mode` is ignored by the API, and `moderation_level` is
        validated but has no effect. Both emit a DeprecationWarning and will be
        removed in 3.0.
        """
        if mode is not None or moderation_level is not None:
            warnings.warn(
                "try_on_fashion: `mode` and `moderation_level` have no effect and will be removed in 3.0",
                DeprecationWarning,
                stacklevel=2,
            )
        body = {
            "model_image": model_image,
            "garment_image": garment_image,
            "category": category,
            "subcategory": subcategory,
            "mode": mode,
            "num_samples": num_samples,
            "output_format": output_format,
            "moderation_level": moderation_level,
        }
        return cast(str, self._request("POST", "/tryon/fashion", body)["jobId"])

    def try_on_hairstyle(
        self,
        *,
        face_image: str,
        haircut: str,
        hair_color: Optional[str] = None,
        num_samples: Optional[int] = None,
        output_format: Optional[str] = None,
    ) -> str:
        """Restyle a person's hair. Returns the job id.

        `num_samples` is 1-4 (charged per image) and `output_format` is "png"
        or "jpeg".
        """
        body = {
            "face_image": face_image,
            "haircut": haircut,
            "hair_color": hair_color,
            "num_samples": num_samples,
            "output_format": output_format,
        }
        return cast(str, self._request("POST", "/tryon/hairstyle", body)["jobId"])

    def try_on_tattoo(
        self,
        *,
        body_image: str,
        design_image: str,
        placement: Optional[str] = None,
        region: Optional[Dict[str, float]] = None,
        num_samples: Optional[int] = None,
        output_format: Optional[str] = None,
    ) -> str:
        """Ink a design onto skin. Returns the job id.

        `placement` is free text ("on the right forearm, small"). `region` pins the
        exact spot: ``{"x", "y", "w", "h"}`` normalized 0-1 from the top-left,
        each side >= 0.06; with it, `placement` only describes size/style.

        `num_samples` is 1-4 (charged per image) and `output_format` is "png"
        or "jpeg".
        """
        body = {
            "body_image": body_image,
            "design_image": design_image,
            "placement": placement,
            "region": region,
            "num_samples": num_samples,
            "output_format": output_format,
        }
        return cast(str, self._request("POST", "/tryon/tattoo", body)["jobId"])

    def get_status(self, job_id: str) -> Status:
        """Fetch the current status of a job. The id is URL-escaped."""
        data = self._request("GET", f"/status/{quote(str(job_id), safe='')}")
        return Status(
            status=data.get("status", "processing"),
            output=data.get("output") or [],
            error=data.get("error"),
        )

    def get_credits(self) -> Credits:
        """Fetch your current credit balance."""
        c = self._request("GET", "/credits")["credits"]
        return Credits(
            on_demand=c.get("on_demand", 0),
            subscription=c.get("subscription", 0),
            purchased=c.get("purchased", 0),
            reserved=c.get("reserved", 0),
        )

    # Live (real-time webcam) try-on. Server side only: the end user's browser
    # streams with the `tryiton-live` npm package, using the response of
    # start_live_session (session-scoped credentials, never your API key).

    def get_live_config(self) -> LiveConfig:
        """Live try-on availability and pricing for your account.

        Returns a dict with ``enabled``, ``secondsPerCredit``, ``maxSeconds``,
        ``minCredits`` and ``maxConcurrentSessions``.
        """
        data = self._request("GET", "/live/config")
        return cast(LiveConfig, {k: v for k, v in data.items() if k != "ok"})

    def prepare_live_garment(
        self,
        garment_image: str,
        *,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
    ) -> LiveGarment:
        """Prepare a garment for live try-on. Returns the garment dict.

        Do it once per product ahead of time (e.g. at catalog sync): it's cached
        per image and category, so starting a session or switching garments
        later is instant. `garment_image` is a URL or base64 data URL. Passing
        `category` (and `subcategory`, e.g. "tops") is recommended; omit it to
        let it be detected.

        The dict has ``id`` (pass it to start_live_session), ``category``,
        ``subcategory``, ``description`` and ``createdAt``.
        """
        body = {
            "garment_image": garment_image,
            "category": category,
            "subcategory": subcategory,
        }
        return cast(LiveGarment, self._request("POST", "/live/garments", body)["garment"])

    def start_live_session(
        self,
        *,
        garment_id: Optional[str] = None,
        max_seconds: Optional[int] = None,
        end_user_id: Optional[str] = None,
        allowed_origin: Optional[str] = None,
    ) -> LiveSessionStart:
        """Start a live session for one end user. Holds the first credit.

        Returns the full response body (``session``, ``clientSecret``,
        ``connection``, ``secondsPerCredit``, ``maxSeconds``, ``secondsLeft``,
        ``garment``). Send it to the browser unchanged; it streams with
        ``connectLiveTryOn`` from the `tryiton-live` npm package.

        `garment_id` is a prepared garment to start with. `max_seconds` caps the
        session (10 to the account's maxSeconds). `end_user_id` is your id for
        the end user: one stream per end user, a restart ends the previous one.
        `allowed_origin` locks the media token to your site, e.g.
        "https://shop.example.com".
        """
        body = {
            "garment_id": garment_id,
            "max_seconds": max_seconds,
            "end_user_id": end_user_id,
            "allowed_origin": allowed_origin,
        }
        return cast(LiveSessionStart, self._request("POST", "/live/sessions", body))

    def get_live_session(self, session_id: str) -> LiveSession:
        """Status and usage of a live session. Returns the session dict."""
        data = self._request("GET", f"/live/sessions/{quote(session_id, safe='')}")
        return cast(LiveSession, data["session"])

    def stop_live_session(self, session_id: str) -> LiveSession:
        """End a live session from your server (e.g. the user left). Idempotent.

        Returns the ended session dict.
        """
        data = self._request("POST", f"/live/sessions/{quote(session_id, safe='')}/stop", {})
        return cast(LiveSession, data["session"])

    def wait_for_result(
        self,
        job_id: str,
        *,
        poll_interval: float = 2.0,
        timeout: float = 120.0,
    ) -> List[str]:
        """Poll a job until it completes, then return the output image URLs.

        Raises TryItOnError if the job fails or the timeout is reached.
        """
        deadline = time.monotonic() + timeout
        while True:
            status = self.get_status(job_id)
            if status.status == "completed":
                return status.output
            if status.status == "failed":
                raise _job_failure(status.error)
            if time.monotonic() > deadline:
                raise TryItOnError(
                    f"Timed out waiting for job {job_id} after {timeout}s.",
                    error_name="Timeout",
                )
            time.sleep(poll_interval)

    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = {"Authorization": f"Bearer {self.api_key}", "User-Agent": self._user_agent}
        payload = None
        if body is not None:
            payload = {k: v for k, v in body.items() if v is not None}
            headers["Content-Type"] = "application/json"

        try:
            resp = self._session.request(
                method, url, headers=headers, json=payload, timeout=self.timeout
            )
        except requests.RequestException as exc:
            raise TryItOnError(f"Network error: {exc}", error_name="NetworkError") from exc

        try:
            data = resp.json() if resp.content else {}
        except ValueError:
            data = {}

        if not resp.ok:
            # API envelope: {"ok": false, "error": {"name", "message"}}. Older shapes put strings at the top level.
            if not isinstance(data, dict):
                data = {}
            error = data.get("error")
            api_error: Dict[str, Any] = error if isinstance(error, dict) else {}
            top_message = data.get("message") if isinstance(data.get("message"), str) else None
            top_name = error if isinstance(error, str) else None
            raise TryItOnError(
                api_error.get("message") or top_message or f"HTTP {resp.status_code}",
                status=resp.status_code,
                error_name=api_error.get("name") or top_name,
            )

        return data


def _job_failure(error: Any) -> TryItOnError:
    """The error for a failed job. `GET /status` sends the reason as a plain string; a
    `{"name", "message"}` dict is still accepted from older API versions."""
    if isinstance(error, dict):
        return TryItOnError(
            error.get("message") or "Try-on failed.",
            error_name=error.get("name") or "ProcessingError",
        )
    message = error if isinstance(error, str) and error else "Try-on failed."
    return TryItOnError(message, error_name="ProcessingError")
