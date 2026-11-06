import sys
import json
import requests
 
username = sys.argv[1]
password = sys.argv[2]
 
AUTH_URL = "http://34.100.128.138:9080/openam/json/realms/root/authenticate"
 
headers = {
    "X-OpenAM-Username": username,
    "X-OpenAM-Password": password,
    "Accept-API-Version": "resource=2.1, protocol=1.0",
    "Content-Type": "application/json"
}
 
response = requests.post(
    AUTH_URL,
    headers=headers,
    timeout=30
)
 
response.raise_for_status()
 
token = response.json()["tokenId"]
 
print(json.dumps({
    "status": "SUCCESS",
    "token": token
}))
