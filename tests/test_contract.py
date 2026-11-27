"""Shared SDK contract cases (tests/fixtures/sdk-cases.json).

The fixture is generated: edit tryiton/backend/api-contract/sdk-cases.json and run
`node tryiton-sdk/sync-contract.mjs`. Canonical names are camelCase; the tables
below map them to this SDK's snake_case methods and keyword arguments.
"""

import dataclasses
import json
import re
from pathlib import Path

import pytest

import tryiton
from tryiton import TryItOnError

CASES = json.loads((Path(__file__).parent / "fixtures" / "sdk-cases.json").read_text(encoding="utf-8"))
BASE_URL = CASES["baseUrl"]
USER_AGENT = f"tryiton-python/{tryiton.__version__}"

METHODS = {
    "tryOnFashion": "try_on_fashion",
    "tryOnHairstyle": "try_on_hairstyle",
    "tryOnTattoo": "try_on_tattoo",
    "getStatus": "get_status",
    "getCredits": "get_credits",
    "waitForResult": "wait_for_result",
    "getLiveConfig": "get_live_config",
    "prepareLiveGarment": "prepare_live_garment",
    "prepareLiveOutfit": "prepare_live_outfit",
    "startLiveSession": "start_live_session",
    "getLiveSession": "get_live_session",
    "stopLiveSession": "stop_live_session",
}

PARAMS = {
    "modelImage": "model_image",
    "garmentImage": "garment_image",
    "category": "category",
    "subcategory": "subcategory",
    "mode": "mode",
    "numSamples": "num_samples",
    "outputFormat": "output_format",
    "moderationLevel": "moderation_level",
    "faceImage": "face_image",
    "haircut": "haircut",
    "hairColor": "hair_color",
    "bodyImage": "body_image",
    "designImage": "design_image",
    "placement": "placement",
    "region": "region",
    "jobId": "job_id",
    "sessionId": "session_id",
    "garmentId": "garment_id",
    "maxSeconds": "max_seconds",
    "endUserId": "end_user_id",
    "allowedOrigin": "allowed_origin",
    "detailImages": "detail_images",
    "description": "description",
    "instructions": "instructions",
    "enhancePrompt": "enhance_prompt",
    "garmentIds": "garment_ids",
}

# Extra kwargs per method, so polling cases run instantly.
EXTRA_KWARGS = {"waitForResult": {"poll_interval": 0}}


def call(client, case):
    method = case["method"]
    assert method in METHODS, f"No Python mapping for contract method {method!r}"
    kwargs = {}
    for name, value in case["params"].items():
        assert name in PARAMS, f"No Python mapping for contract param {name!r}"
        kwargs[PARAMS[name]] = value
    kwargs.update(EXTRA_KWARGS.get(method, {}))
    return getattr(client, METHODS[method])(**kwargs)


def plain(value):
    """Status and Credits are dataclasses; compare them as the dicts the fixture lists."""
    return dataclasses.asdict(value) if dataclasses.is_dataclass(value) else value


def assert_request(prepared, expected):
    assert prepared.method == expected["method"]
    assert prepared.url.startswith(BASE_URL), prepared.url
    assert prepared.url[len(BASE_URL):] == expected["path"]
    assert prepared.headers["Authorization"] == CASES["authHeader"]
    assert prepared.headers["User-Agent"] == USER_AGENT
    if "body" in expected:
        assert prepared.headers["Content-Type"] == "application/json"
        assert json.loads(prepared.body) == expected["body"]
    if expected["method"] == "GET":
        assert prepared.body is None


def assert_error(err, expected):
    assert err.status == expected["status"]
    assert err.error_name == expected["errorName"]
    if "messageAnyOf" in expected:
        assert str(err) in expected["messageAnyOf"]
    else:
        assert str(err) == expected["message"]


def test_user_agent_matches_contract_pattern():
    assert re.match(CASES["userAgent"]["pattern"], USER_AGENT)


@pytest.mark.parametrize("case", CASES["methodCases"], ids=[c["name"] for c in CASES["methodCases"]])
def test_method_case(make_client, case):
    client, adapter = make_client(case["responses"], api_key=CASES["apiKey"], base_url=BASE_URL)

    if "expectError" in case:
        with pytest.raises(TryItOnError) as info:
            call(client, case)
        assert_error(info.value, case["expectError"])
    else:
        result = call(client, case)
        if case.get("expectResultIsResponseBody"):
            assert result == case["responses"][-1]["body"]
        else:
            assert plain(result) == case["expectResult"]

    assert len(adapter.requests) == len(case["expectRequests"])
    for prepared, expected in zip(adapter.requests, case["expectRequests"]):
        assert_request(prepared, expected)


ERROR_TARGETS = {
    "get_credits": (lambda c: c.get_credits(), "/credits"),
    "get_live_session": (lambda c: c.get_live_session("s1"), "/live/sessions/s1"),
}


@pytest.mark.parametrize("target", list(ERROR_TARGETS))
@pytest.mark.parametrize("case", CASES["errorCases"], ids=[c["name"] for c in CASES["errorCases"]])
def test_error_case(make_client, case, target):
    client, adapter = make_client([case["response"]], api_key=CASES["apiKey"], base_url=BASE_URL)
    invoke, path = ERROR_TARGETS[target]

    with pytest.raises(TryItOnError) as info:
        invoke(client)

    assert_error(info.value, case["expectError"])
    assert_request(adapter.requests[0], {"method": "GET", "path": path})
