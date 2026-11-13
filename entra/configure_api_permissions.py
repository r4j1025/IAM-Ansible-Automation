import sys
import urllib.parse

from graph_client import GRAPH_BASE, graph_json, load_payload, log, require_env


GRAPH_APP_ID = "00000003-0000-0000-c000-000000000000"


def main():
    token = require_env("ACCESS_TOKEN")
    app_object_id = require_env("APPLICATION_OBJECT_ID")
    payload = load_payload()

    query = urllib.parse.urlencode({
        "$filter": f"appId eq '{GRAPH_APP_ID}'",
    })
    _, body = graph_json(
        "GET", f"{GRAPH_BASE}/servicePrincipals?{query}",
        token, expected={200},
    )
    graph_sps = body.get("value") or []
    if not graph_sps:
        raise RuntimeError("Microsoft Graph service principal was not found.")

    graph_sp = graph_sps[0]
    scopes = graph_sp.get("oauth2PermissionScopes") or []
    roles = graph_sp.get("appRoles") or []

    resource_access = []
    admin_required = []
    admin_not_required = []
    unresolved = []

    for row in payload.get("api_permission_details") or []:
        permission = row.get("access")
        permission_type = row.get("api_permission_type")

        if not permission:
            continue

        log(f"Resolving permission: {permission} ({permission_type})")
        if permission_type == "delegated":
            match = next((item for item in scopes
                          if item.get("value") == permission), None)
            access_type = "Scope"
            if match:
                if match.get("type") == "Admin":
                    admin_required.append(f"{permission} (Delegated)")
                else:
                    admin_not_required.append(f"{permission} (Delegated)")
        elif permission_type == "application":
            match = next((item for item in roles
                          if item.get("value") == permission), None)
            access_type = "Role"
            if match:
                admin_required.append(f"{permission} (Application)")
        else:
            log(f"Unsupported permission type; skipping: {permission_type}")
            continue

        if not match:
            unresolved.append(f"{permission} ({permission_type})")
            log(f"Permission not found in Microsoft Graph: {permission}")
            continue

        resource_access.append({"id": match["id"], "type": access_type})

    patch_body = {
        "requiredResourceAccess": [{
            "resourceAppId": GRAPH_APP_ID,
            "resourceAccess": resource_access,
        }]
    }

    status, _ = graph_json(
        "PATCH", f"{GRAPH_BASE}/applications/{app_object_id}",
        token, patch_body, expected={204},
    )

    log("API Permissions updated successfully.")
    log("Permissions requiring admin consent: "
        + (", ".join(sorted(set(admin_required))) or "None"))
    log("Permissions not requiring admin consent: "
        + (", ".join(sorted(set(admin_not_required))) or "None"))
    if unresolved:
        log("Unresolved permissions: " + ", ".join(unresolved))

    # Keep the same ADC meaning as the Harness pipeline.
    log("ADC=" + ("Yes" if admin_required else "No"))
    log(f"API permission configuration completed (HTTP {status}).")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
