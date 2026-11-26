"""Unit tests for behavior the shared contract cases don't cover."""

import re
from pathlib import Path

import pytest
import requests

import tryiton
from tryiton import TryItOn, TryItOnError

PROCESSING = {"status": 200, "body": {"ok": True, "status": "processing", "output": [], "error": None}}


def test_version_matches_pyproject():
    pyproject = (Path(__file__).parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    # tomllib is 3.11+; the [project] version line is simple enough to match directly.
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    assert match, "no version in pyproject.toml"
    assert tryiton.__version__ == match.group(1)


def test_py_typed_marker_ships_with_the_package():
    assert (Path(tryiton.__file__).parent / "py.typed").is_file()


@pytest.mark.parametrize("api_key", ["", None])
def test_missing_api_key(api_key):
    with pytest.raises(TryItOnError) as info:
        TryItOn(api_key=api_key)
    assert info.value.error_name == "ConfigError"
    assert info.value.status is None


def test_default_base_url_and_trailing_slash(make_client):
    client, adapter = make_client([{"status": 200, "body": {"ok": True, "credits": {}}}])
    client.get_credits()
    assert adapter.requests[0].url == "https://tryiton.now/api/v1/credits"

    client, adapter = make_client([{"status": 200, "body": {"ok": True, "credits": {}}}], base_url="https://x.test/v1/")
    client.get_credits()
    assert adapter.requests[0].url == "https://x.test/v1/credits"


def test_user_agent_overrides_session_default(make_client):
    client, adapter = make_client([{"status": 200, "body": {"ok": True, "credits": {}}}])
    client._session.headers["User-Agent"] = "custom/1.0"
    client.get_credits()
    assert adapter.requests[0].headers["User-Agent"] == f"tryiton-python/{tryiton.__version__}"


def test_request_timeout_is_passed_to_transport(make_client):
    client, adapter = make_client([{"status": 200, "body": {"ok": True, "credits": {}}}], timeout=7.5)
    client.get_credits()
    assert adapter.timeouts == [7.5]


@pytest.mark.parametrize(
    "exc",
    [requests.ConnectionError("connection refused"), requests.Timeout("read timed out")],
    ids=["connection", "timeout"],
)
def test_transport_errors_map_to_network_error(make_client, exc):
    client, _ = make_client([exc])
    with pytest.raises(TryItOnError) as info:
        client.get_credits()
    assert info.value.error_name == "NetworkError"
    assert info.value.status is None
    assert str(exc) in str(info.value)
    assert info.value.__cause__ is exc


def test_get_credits_defaults_missing_buckets_to_zero(make_client):
    client, _ = make_client([{"status": 200, "body": {"ok": True, "credits": {"subscription": 3}}}])
    assert client.get_credits() == tryiton.Credits(on_demand=0, subscription=3, purchased=0, reserved=0)


def test_wait_for_result_times_out(make_client):
    client, adapter = make_client([PROCESSING])
    # A negative timeout puts the deadline in the past, so the first poll is the last.
    with pytest.raises(TryItOnError) as info:
        client.wait_for_result("job_1", poll_interval=0, timeout=-1)
    assert info.value.error_name == "Timeout"
    assert info.value.status is None
    assert len(adapter.requests) == 1


def test_wait_for_result_failed_without_reason(make_client):
    client, _ = make_client([{"status": 200, "body": {"ok": True, "status": "failed", "output": [], "error": None}}])
    with pytest.raises(TryItOnError) as info:
        client.wait_for_result("job_1", poll_interval=0)
    assert str(info.value) == "Try-on failed."
    assert info.value.error_name == "ProcessingError"


def test_wait_for_result_accepts_legacy_error_object(make_client):
    legacy = {"name": "ModerationError", "message": "Blocked by moderation."}
    client, _ = make_client([{"status": 200, "body": {"ok": True, "status": "failed", "output": [], "error": legacy}}])
    with pytest.raises(TryItOnError) as info:
        client.wait_for_result("job_1", poll_interval=0)
    assert str(info.value) == "Blocked by moderation."
    assert info.value.error_name == "ModerationError"


def test_wait_for_result_surfaces_http_errors(make_client):
    error = {"status": 404, "body": {"ok": False, "error": {"name": "AppError", "message": "Tryon not found."}}}
    client, _ = make_client([PROCESSING, error])
    with pytest.raises(TryItOnError) as info:
        client.wait_for_result("job_1", poll_interval=0)
    assert (info.value.status, info.value.error_name, str(info.value)) == (404, "AppError", "Tryon not found.")


def test_typed_responses_are_plain_dicts(make_client):
    garment = {"id": "g1", "category": "clothing", "subcategory": None, "description": None, "createdAt": "x"}
    client, _ = make_client([{"status": 201, "body": {"ok": True, "garment": garment}}])
    result = client.prepare_live_garment("https://example.com/shirt.jpg")
    assert type(result) is dict
    assert result == garment
