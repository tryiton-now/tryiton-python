"""TryItOn API client."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

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


@dataclass
class Status:
    """A job's status snapshot."""

    status: str  # "processing" | "completed" | "failed"
    output: List[str]
    error: Optional[Dict[str, str]]


@dataclass
class Credits:
    on_demand: int
    subscription: int
    purchased: int
    reserved: int


class TryItOn:
    """Client for the TryItOn virtual try-on API.

    Example:
        client = TryItOn(api_key="...")
        job_id = client.try_on_clothes(
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

    # ── Try-on submissions ────────────────────────────────────────────────

    def try_on_clothes(
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
        `output_format` is "png" or "jpeg", and `moderation_level` is one of
        "conservative", "permissive", or "none".
        """
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
        return self._request("POST", "/tryon/clothes", body)["jobId"]

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
        return self._request("POST", "/tryon/hairstyle", body)["jobId"]

    def try_on_tattoo(
        self,
        *,
        body_image: str,
        design_image: str,
        placement: Optional[str] = None,
        num_samples: Optional[int] = None,
        output_format: Optional[str] = None,
    ) -> str:
        """Ink a design onto skin. Returns the job id.

        `num_samples` is 1-4 (charged per image) and `output_format` is "png"
        or "jpeg".
        """
        body = {
            "body_image": body_image,
            "design_image": design_image,
            "placement": placement,
            "num_samples": num_samples,
            "output_format": output_format,
        }
        return self._request("POST", "/tryon/tattoo", body)["jobId"]

    # ── Status & credits ──────────────────────────────────────────────────

    def get_status(self, job_id: str) -> Status:
        """Fetch the current status of a job."""
        data = self._request("GET", f"/status/{job_id}")
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
                err = status.error or {}
                raise TryItOnError(
                    err.get("message", "Try-on failed."),
                    error_name=err.get("name", "ProcessingError"),
                )
            if time.monotonic() > deadline:
                raise TryItOnError(
                    f"Timed out waiting for job {job_id} after {timeout}s.",
                    error_name="Timeout",
                )
            time.sleep(poll_interval)

    # ── Internals ─────────────────────────────────────────────────────────

    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
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
            raise TryItOnError(
                data.get("message", f"HTTP {resp.status_code}"),
                status=resp.status_code,
                error_name=data.get("error"),
            )

        return data
