import sys
import urllib.parse

from graph_client import GRAPH_BASE, graph_json, load_payload, log, require_env


APP_ROLE_ID_DEFAULT_ACCESS = "00000000-0000-0000-0000-000000000000"


def main():
    token = require_env("ACCESS_TOKEN")
    enterprise_object_id = require_env("ENTERPRISE_OBJ_ID")
    payload = load_payload()
    groups = payload.get("group_names") or []

    if not groups:
        log("No groups supplied; skipping group assignment.")
        return

    assigned = []
    failed = []

    for item in groups:
        group_name = item.get("group_name") if isinstance(item, dict) else item
        if not group_name:
            continue

        group_name = str(group_name).strip()
        log(f"Searching Entra group: {group_name}")
        safe_name = group_name.replace("'", "''")
        query = urllib.parse.urlencode({
            "$filter": f"displayName eq '{safe_name}'",
            "$select": "id,displayName",
        })
        _, body = graph_json(
            "GET", f"{GRAPH_BASE}/groups?{query}",
            token, expected={200},
        )
        matches = body.get("value") or []
        if not matches:
            failed.append(f"{group_name}: group not found")
            log(f"Group not found: {group_name}")
            continue
        if len(matches) > 1:
            failed.append(f"{group_name}: multiple exact matches")
            log(f"Multiple exact group matches: {group_name}")
            continue

        group_id = matches[0]["id"]
        assignment = {
            "principalId": group_id,
            "resourceId": enterprise_object_id,
            "appRoleId": APP_ROLE_ID_DEFAULT_ACCESS,
        }
        status, raw = graph_json(
            "POST",
            f"{GRAPH_BASE}/groups/{group_id}/appRoleAssignments",
            token, assignment, expected={201, 409},
        )
        if status == 201:
            assigned.append(group_name)
            log(f"Group assigned successfully: {group_name}")
        elif status == 409:
            # A conflict can indicate that this assignment already exists.
            assigned.append(group_name)
            log(f"Group already assigned: {group_name}")
        else:
            failed.append(f"{group_name}: HTTP {status} {raw}")

    if failed:
        raise RuntimeError(
            "One or more group assignments failed: " + "; ".join(failed)
        )

    log("Group assignment completed.")
    log("Groups assigned/already assigned: " + ", ".join(assigned))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
