import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from graph_client import emit_result, log


def main():
    tenant_id = os.environ.get("TENANT_ID", "").strip()
    client_id = os.environ.get("CLIENT_ID", "").strip()
    client_secret = os.environ.get("CLIENT_SECRET", "")

    if not tenant_id or not client_id or not client_secret:
        raise RuntimeError(
            "TENANT_ID, CLIENT_ID, and CLIENT_SECRET must be supplied "
            "through AAP credentials/variables."
        )

    log("Requesting Microsoft Graph access token...")
    form = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }).encode("utf-8")

    request = urllib.request.Request(
        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        data=form,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            details = json.loads(raw)
        except json.JSONDecodeError:
            details = {"error_description": raw}
        raise RuntimeError(
            "Token request failed: "
            + json.dumps({
                "error": details.get("error"),
                "error_description": details.get("error_description"),
            })
        ) from exc

    token = body.get("access_token")
    if not token:
        raise RuntimeError(
            "Token response did not contain access_token: "
            + json.dumps({
                "error": body.get("error"),
                "error_description": body.get("error_description"),
            })
        )

    log("Microsoft Graph access token generated.")
    # stdout is captured by Ansible; do not print the token in job logs.
    emit_result({"access_token": token})


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
