"""Shared test helpers: a fake requests transport adapter mounted on a real Session.

Stubbing at the adapter keeps the client's real request building (headers, JSON
encoding, URL quoting) under test; only the network hop is replaced.
"""

import json
from typing import Any, Callable, Dict, List, Optional

import pytest
import requests
from requests.adapters import BaseAdapter

import tryiton


class FakeAdapter(BaseAdapter):
    """Replies with queued (status, body) pairs in order and records every request.

    A queued item that is an exception instance is raised instead, to simulate a
    transport failure.
    """

    def __init__(self, replies: List[Any]):
        super().__init__()
        self.replies = list(replies)
        self.requests: List[requests.PreparedRequest] = []
        self.timeouts: List[Any] = []

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        self.requests.append(request)
        self.timeouts.append(timeout)
        if not self.replies:
            raise AssertionError(f"Unexpected extra request: {request.method} {request.url}")
        reply = self.replies.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        return build_response(request, reply)

    def close(self):
        pass


def build_response(request: requests.PreparedRequest, reply: Dict[str, Any]) -> requests.Response:
    """A Response from a fixture reply: ``{"status", "body"}`` (JSON) or ``{"status", "raw"}``."""
    resp = requests.Response()
    resp.status_code = reply["status"]
    resp.request = request
    resp.url = request.url or ""
    if "raw" in reply:
        resp._content = reply["raw"].encode("utf-8")
        resp.headers["Content-Type"] = "text/html"
    else:
        resp._content = json.dumps(reply["body"]).encode("utf-8")
        resp.headers["Content-Type"] = "application/json"
    resp.encoding = "utf-8"
    return resp


@pytest.fixture
def make_client() -> Callable[..., Any]:
    """Build ``(client, adapter)``: a TryItOn client whose session replies with `replies`."""

    def factory(replies: List[Any], *, api_key: str = "test-key", base_url: Optional[str] = None, **kwargs: Any):
        adapter = FakeAdapter(replies)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        if base_url is not None:
            kwargs["base_url"] = base_url
        return tryiton.TryItOn(api_key=api_key, session=session, **kwargs), adapter

    return factory
