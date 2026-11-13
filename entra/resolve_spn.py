import json
import sys
import urllib.parse

from graph_client import (
    GRAPH_BASE, emit_result, graph_json, load_payload, log, require_env
)

SPN_KEYS = (
    "spn", "spn_name", "spnName", "SPN", "name",
    "displayName", "application_name",
)


def extract_spn(value):
    """Accept a plain SPN string or a JSON object/string/list."""
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in SPN_KEYS:
            candidate = value.get(key)
            if candidate:
                return str(candidate).strip()
        return ""
    if isinstance(value, list):
        return extract_spn(value[0]) if value else ""
    if isinstance(value, str):
        raw = value.strip()
        if not raw or raw.lower() == "null":
            return ""
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        if isinstance(parsed, str):
            return parsed.strip()
        return extract_spn(parsed)
    return str(value).strip()


def main():
    token = require_env("ACCESS_TOKEN")
    payload = load_payload()
    request_details = payload.get("request_details") or {}
    environments = payload.get("application_environment") or []

    # Always use the first application environment object (index 0).
    # sc_task_number is unrelated to the application_environment array index.
    if not isinstance(environments, list) or not environments:
        raise RuntimeError(
            "application_environment must contain at least one environment object."
        )

    selected_environment = environments[0] or {}
    if not isinstance(selected_environment, dict):
        raise RuntimeError("application_environment[0] must be an object.")

    spn = extract_spn(selected_environment.get("spn"))
    if not spn:
        raise RuntimeError(
            "No SPN was found in ServiceNow payload. Supported locations: "
            "application_environment[0].spn."
        )

    log(f"Searching Entra ID for application display name: {spn}")
    escaped = spn.replace("'", "''")

    def search_apps(filter_expression):
        query = urllib.parse.urlencode({
            "$filter": filter_expression,
            "$select": "id,appId,displayName,createdDateTime,signInAudience",
        })
        _, body = graph_json(
            "GET", f"{GRAPH_BASE}/applications?{query}", token,
            expected={200},
        )
        return body.get("value") or []

    apps = search_apps(f"displayName eq '{escaped}'")
    if not apps:
        log("No exact match. Trying startswith search...")
        apps = search_apps(f"startswith(displayName,'{escaped}')")

    result = {
        "APP_DETECTED": "true" if apps else "false",
        "APP_MATCH_COUNT": str(len(apps)),
        "APPLICATION_OBJECT_ID": "",
        "APPLICATION_CLIENT_ID": "",
        "APPLICATION_DISPLAY_NAME": "",
        "APPLICATION_MATCHES": json.dumps(
            apps, separators=(",", ":")
        ),
        "ENTERPRISE_OBJ_ID": "",
    }

    if not apps:
        log(f"No Entra application matched SPN '{spn}'.")
        emit_result(result)
        return

    # Do not choose an arbitrary app when the search returns multiple matches.
    # Return the requested output variables, then let Ansible stop before changes.
    if len(apps) > 1:
        log("Multiple applications matched; refusing to modify an ambiguous target.")
        log(json.dumps(apps, indent=2))
        emit_result(result)
        return

    app = apps[0]
    result["APPLICATION_OBJECT_ID"] = app["id"]
    result["APPLICATION_CLIENT_ID"] = app["appId"]
    result["APPLICATION_DISPLAY_NAME"] = app.get("displayName", "")

    log(f"Application found: {app.get('displayName', '')}")
    log(f"Application Object ID: {app['id']}")
    log(f"Application Client ID: {app['appId']}")

    # Resolve the Enterprise Application (service principal) using appId.
    client_id = app["appId"].replace("'", "''")
    query = urllib.parse.urlencode({
        "$filter": f"appId eq '{client_id}'",
        "$select": "id,appId,displayName",
    })
    _, body = graph_json(
        "GET", f"{GRAPH_BASE}/servicePrincipals?{query}", token,
        expected={200},
    )
    service_principals = body.get("value") or []
    if not service_principals:
        log("App Registration found, but its Enterprise Application was not found.")
        emit_result(result)
        return
    if len(service_principals) > 1:
        log(
            f"Expected one service principal for client ID {app['appId']}, "
            f"but found {len(service_principals)}."
        )
        emit_result(result)
        return

    enterprise = service_principals[0]
    result["ENTERPRISE_OBJ_ID"] = enterprise["id"]
    log(f"Enterprise Application Object ID: {enterprise['id']}")
    emit_result(result)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
