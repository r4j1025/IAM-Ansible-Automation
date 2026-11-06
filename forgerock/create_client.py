import json
import sys
import requests
 
token = sys.argv[1]
payload = json.loads(sys.argv[2])
 
application_code = payload["request_details"]["application_code"]
 
redirect_uri = payload["application_environment"][0]["redirect_uri"]
 
client_name = application_code.upper() + "_POC_TESTING"
 
url = (
    "http://34.100.128.138:9080/openam/json/"
    "realms/root/realms/oidc-apps/"
    "realm-config/agents/OAuth2Client/"
    + client_name
)
 
request_body = {
    "coreOAuth2ClientConfig": {
        "clientType": "Confidential",
        "redirectionUris": [
            redirect_uri
        ],
        "scopes": [
            "openid",
            "profile",
            "email"
        ],
        "defaultScopes": [
            "openid"
        ]
    }
}
 
headers = {
    "iPlanetDirectoryPro": token,
    "Accept-API-Version": "resource=2.0",
    "Content-Type": "application/json"
}
 
response = requests.put(
    url,
    headers=headers,
    json=request_body,
    timeout=30
)
 
response.raise_for_status()
 
print(json.dumps({
    "status": "SUCCESS",
    "client_name": client_name,
    "redirect_uri": redirect_uri
}))
