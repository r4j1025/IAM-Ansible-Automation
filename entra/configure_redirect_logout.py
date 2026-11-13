import re
import sys
from urllib.parse import urlsplit

from graph_client import GRAPH_BASE, graph_json, load_payload, log, require_env


def clean_url(raw):
    if not raw:
        return ""
    stripped = re.sub(r"<[^>]*>", "", str(raw)).strip()
    match = re.search(r'https?://[^\s<>"]+', stripped, re.IGNORECASE)
    candidate = match.group(0).rstrip(".,;") if match else ""
    if not candidate:
        return ""
    parsed = urlsplit(candidate)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    return candidate


def main():
    token = require_env("ACCESS_TOKEN")
    app_object_id = require_env("APPLICATION_OBJECT_ID")
    payload = load_payload()

    environments = payload.get("application_environment") or []
    if not isinstance(environments, list) or not environments:
        raise RuntimeError(
            "application_environment must contain at least one environment object."
        )

    # Always use the first application environment object (index 0).
    # sc_task_number is not used to select this array entry.
    env = environments[0] or {}
    if not isinstance(env, dict):
        raise RuntimeError("application_environment[0] must be an object.")
    app_type = (
        (payload.get("request_details") or {}).get("application_platform_type")
        or ""
    ).lower()

    raw_redirect = env.get("redirect_uri") or ""
    raw_logout = env.get("logout_uri") or ""
    redirect_uri = clean_url(raw_redirect)
    logout_uri = clean_url(raw_logout)

    if raw_redirect and not redirect_uri:
        raise RuntimeError(f"Invalid Redirect URI: {raw_redirect}")
    if raw_logout and not logout_uri:
        raise RuntimeError(f"Invalid Logout URI: {raw_logout}")

    log(f"Application platform type: {app_type}")
    log("Selected environment index: 0")

    if app_type == "app2app":
        log("App2App: Redirect URI and Logout URI are not applicable; skipping.")
        return

    if app_type == "web":
        if not redirect_uri and not logout_uri:
            log("No Redirect URI or Logout URI supplied; skipping.")
            return
        web = {}
        if redirect_uri:
            web["redirectUris"] = [redirect_uri]
        if logout_uri:
            web["logoutUrl"] = logout_uri
        body = {"web": web}
    elif app_type == "spa":
        if not redirect_uri:
            log("No SPA Redirect URI supplied; skipping.")
            return
        body = {"spa": {"redirectUris": [redirect_uri]}}
    elif app_type in ("mobileapp", "mobile_desktop_app"):
        if not redirect_uri:
            log("No Mobile Redirect URI supplied; skipping.")
            return
        body = {"publicClient": {"redirectUris": [redirect_uri]}}
    else:
        raise RuntimeError(f"Unsupported application platform type: {app_type}")

    status, _ = graph_json(
        "PATCH", f"{GRAPH_BASE}/applications/{app_object_id}",
        token, body, expected={204},
    )
    log(f"Redirect / Logout URI configuration completed (HTTP {status}).")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
