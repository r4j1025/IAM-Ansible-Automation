import json
import sys
import requests
 
token = sys.argv[1]
payload = json.loads(sys.argv[2])
 
request_details = payload["request_details"]
app_env = payload["application_environment"][0]
 
application_code = request_details["application_code"].upper()
 
client_id = f"{application_code}_DEMO_ONBOARDING"
 
redirect_uri = app_env.get("redirect_uri", "")
logout_uri = app_env.get("logout_uri", "")
 
grant_type = request_details.get("grant_type", "")
additional_scope = request_details.get("additional_scope", "")
token_auth_method = request_details.get(
    "token_endpoint_auth_method",
    ""
)
 
custom_process_id = request_details.get(
    "custom_process_id",
    ""
)
 
#
# Grant type mapping
#
grant_type_map = {
    "authorization_code": ["authorization_code"],
    "authorization_code_pkce": ["authorization_code"],
    "client_credentials": ["client_credentials"],
    "device_code_flow": ["urn:ietf:params:oauth:grant-type:device_code"]
}
 
grant_types = grant_type_map.get(
    grant_type.lower(),
    ["authorization_code"]
)
 
#
# Token endpoint auth method mapping
#
auth_method_map = {
    "client_sec_post": "client_secret_post",
    "client_secret_post": "client_secret_post",
    "client_sec_basic": "client_secret_basic",
    "client_secret_basic": "client_secret_basic"
}
 
token_endpoint_auth_method = auth_method_map.get(
    token_auth_method.lower(),
    "client_secret_basic"
)
 
#
# Scope mapping
#
scopes = ["openid", "profile", "email"]
 
additional_scope_lower = additional_scope.lower()
 
if "edir" in additional_scope_lower:
    scopes.append("nsroles")
 
if "ad" in additional_scope_lower:
    scopes.append("LdapGroups")
 
scopes = list(set(scopes))
 
#
# Description
#
description = (
    f"APPCODE={application_code},SAID=said"
)
 
#
# Custom properties
#
custom_properties = []
 
if custom_process_id:
    custom_properties.append(
        f"processid={custom_process_id}"
    )
 
url = (
    "http://34.100.128.138:9080/openam/json/"
    "realms/root/realms/oidc-apps/"
    "realm-config/agents/OAuth2Client/"
    + client_id
)
 
request_body = {
    "coreOAuth2ClientConfig": {
        "clientType": "Confidential",
        "redirectionUris": [
            redirect_uri
        ],
        "scopes": scopes,
        "defaultScopes": [
            "openid"
        ],
        "description": description
    },
 
    "advancedOAuth2ClientConfig": {
        "grantTypes": grant_types,
        "tokenEndpointAuthMethod":
            token_endpoint_auth_method
    },
 
    "coreOpenIDClientConfig": {
        "postLogoutRedirectUri": [
            logout_uri
        ]
    }
}
 
#
# Custom Properties
#
if custom_properties:
    request_body[
        "advancedOAuth2ClientConfig"
    ]["customProperties"] = custom_properties
 
headers = {
    "iPlanetDirectoryPro": token,
    "Accept-API-Version": "resource=2.0",
    "Content-Type": "application/json"
}
 
print(
    json.dumps(
        request_body,
        indent=2
    )
)
 
response = requests.put(
    url,
    headers=headers,
    json=request_body,
    timeout=30
)
 
if response.status_code >= 400:
    print("HTTP_STATUS:", response.status_code)
    print("RESPONSE_BODY:")
    print(response.text)
    sys.exit(1)
 
print(
    json.dumps({
        "status": "SUCCESS",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "logout_uri": logout_uri,
        "grant_type": grant_type,
        "token_endpoint_auth_method":
            token_endpoint_auth_method
    })
)