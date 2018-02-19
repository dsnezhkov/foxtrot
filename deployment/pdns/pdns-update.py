import requests
import json
 
## Local update
#uri = 'http://127.0.0.1:8081/api/v1/servers/localhost/zones/s3bucket.stream'

# Remote update w/Niginx proxy
uri = 'https://138.68.234.147/api/v1/servers/localhost/zones/s3bucket.stream'
headers = { 'X-API-Key':  '****' }
 
payload = {
    "rrsets": [
        {
            "name": "0db5fc85eadc1bf5d9e1d6e887bfd9a7._domainkey.s3bucket.stream.",
            "type": "TXT",
            "ttl": 3600,
            "changetype": "REPLACE",
            "records": [
                {
                    "content": '"v=DKIM1; h=sha256; k=rsa; t=y; s=email; p=MIIBIjANBgkqhkiG9w0BAQEAQEAulU+SIDAQAB"',
                    "disabled": False
                }
            ]
        }
    ]
}
 
# Valid SSL cert
# r = requests.patch(uri, data=json.dumps(payload), headers=headers)

# Bypassing self-signed verification
r = requests.patch(uri, data=json.dumps(payload), headers=headers, verify=False)
print r.text

