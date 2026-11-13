"""Small Microsoft Graph HTTP client shared by the onboarding scripts."""
import json
import sys
import urllib.error
import urllib.request


GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def log(message):
    print(message, file=sys.stderr, flush=True)


def graph_request(method, url, token, body=None, timeout=60):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url, data=data, method=method, headers=headers
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return response.status, raw
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Microsoft Graph connection failed: {exc}") from exc


def graph_json(method, url, token, body=None, expected=None):
    status, raw = graph_request(method, url, token, body)
    if expected is not None and status not in expected:
        raise RuntimeError(
            f"Graph {method} request failed (HTTP {status}): {raw}"
        )
    if not raw:
        return status, {}
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError(
            f"Graph returned non-JSON response (HTTP {status}): {raw}"
        )


def emit_result(result):
    """Write exactly one JSON object to stdout for Ansible from_json."""
    print(json.dumps(result, separators=(",", ":")), flush=True)


def require_env(name):
    import os
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"Required environment variable {name} is missing")
    return value


def load_payload():
    import os
    raw = os.environ.get("TRIGGER_PAYLOAD", "")
    if not raw:
        raise RuntimeError("TRIGGER_PAYLOAD is missing")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"TRIGGER_PAYLOAD is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("TRIGGER_PAYLOAD must be a JSON object")
    return payload
