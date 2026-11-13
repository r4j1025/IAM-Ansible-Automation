import sys

from graph_client import GRAPH_BASE, graph_json, load_payload, log, require_env


def main():
    token = require_env("ACCESS_TOKEN")
    app_object_id = require_env("APPLICATION_OBJECT_ID")
    payload = load_payload()
    claims = payload.get("optional_claims") or []

    if not claims:
        log("No optional claims supplied; skipping.")
        return

    def build(token_type):
        result = []
        for claim in claims:
            if claim.get("token_type") == token_type and claim.get("claim"):
                result.append({
                    "name": claim["claim"],
                    "essential": False,
                    "additionalProperties": [],
                })
        return result

    body = {
        "optionalClaims": {
            "idToken": build("id"),
            "accessToken": build("access"),
        }
    }

    status, _ = graph_json(
        "PATCH", f"{GRAPH_BASE}/applications/{app_object_id}",
        token, body, expected={204},
    )
    log(f"Optional Claims configured successfully (HTTP {status}).")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
