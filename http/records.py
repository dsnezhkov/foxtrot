#!/usr/bin/env python
import requests
import json

""" import time
# pip install git+https://github.com/pieterlexis/pdns_api_client-py.git
import pdns_api_client
from pdns_api_client.rest import ApiException
from pprint import pprint


# Configure API key authorization: APIKeyHeader
pdns_api_client.configuration.api_key['X-API-Key'] = '**********'
pdns_api_client.configuration.host = "https://138.68.234.147/api/v1"
pdns_api_client.configuration.verify_ssl = False # Set to True if valid cert


server_id = 'localhost'
zone_name = 's3b.stream.'
zone_kind = 'Native'
zone_soa_edit_api = 'INCEPTION-INCREMENT'
nameservers = ["ns1.s3b.stream.", "ns2.s3b.stream."]


zone_struct = pdns_api_client.Zone()
api_instance = pdns_api_client.ZonesApi()
rrsets = True

## @ RRSet
record_top = pdns_api_client.Record(
    content="ns1.s3bucket.stream. hostmaster.s3bucket.stream. 1508130754 10800 3600 604800 1800", disabled=False)
#records_top = [record_top]
rrset_SOA = pdns_api_client.RRSet(
    name="s3b.stream.", type="SOA", ttl=3600, changetype="REPLACE", records=[record_top], comments=None)

## NS
record_NS_ns1 = pdns_api_client.Record(
    content="ns1.s3b.stream.", disabled=False)
record_NS_ns2 = pdns_api_client.Record(
    content="ns2.s3b.stream.", disabled=False)

rrset_NS = pdns_api_client.RRSet(
    name="s3b.stream.", type="NS", ttl=3600, changetype="REPLACE",  records=[record_NS_ns1, record_NS_ns2],
    comments=None)

## A
record_ns1 = pdns_api_client.Record(
    content="138.68.234.147", disabled=False)
rrset_A_ns1 = pdns_api_client.RRSet(
    name="ns1.s3b.stream.", type="A", ttl=3600, changetype="REPLACE", records=[record_ns1], comments=None)

record_ns2 = pdns_api_client.Record(
    content="138.68.234.147", disabled=False)
rrset_A_ns2 = pdns_api_client.RRSet(
    name="ns2.s3b.stream.", type="A", ttl=3600, changetype="REPLACE", records=[record_ns2], comments=None)

## TXT
record_dkim = pdns_api_client.Record(content='"v=DKIM1; h=sha256; k=rsa; t=y; s=email; p=XXXXXXXXXXXX"', disabled=False)
rrset_TXT = pdns_api_client.RRSet(
    name="352d079ffdaddd23edd407ff32a66c48._domainkey.s3bucket.stream.",
    type="TXT", ttl=3600, changetype="REPLACE", records=[record_dkim], comments=None)

rrsets_update = [rrset_SOA, rrset_NS, rrset_A_ns1, rrset_A_ns2, rrset_TXT]
#zone_struct.rrsets = rrsets_update
#zone_struct.soa_edit_api = zone_soa_edit_api
#zone_struct.kind = zone_kind
#zone_struct.nameservers = nameservers
#pprint(zone_struct)

pprint(rrsets_update)
try:
    # Modifies basic zone data (metadata).
    # api_instance.put_zone(server_id, zone_id, zone_struct)
    # Creates a new domain, returns the Zone on creation.
    api_response = api_instance.list_zone(server_id, 's3bucket.stream')
    pprint(api_response)
except ApiException as e:
    #print("Exception when calling ZonesApi->put_zone: %s\n" % e)
    print("Exception when calling ZonesApi->create_zone: %s\n" % e)


exit(2)
"""

zone_uri = 'https://138.68.234.147/api/v1/servers/localhost/zones/s3bucket.stream'
#rec_uri = 'https://138.68.234.147/api/v1/servers/localhost/search-data'
headers = { 'X-API-Key':  '**********' }

def precord_get():
    r = requests.get(zone_uri, headers=headers, verify=False)
    print(r.text)

def precord(payload):
    # r = requests.patch(uri, data=json.dumps(payload), headers=headers)
    # For bypassing self-signed verification
    r = requests.patch(zone_uri, data=json.dumps(payload), headers=headers, verify=False)
    print(r.text)

r_replace_p = {
    "rrsets": [
        {
            "name": "352d079ffdaddd23edd407ff32a66c48._domainkey.s3bucket.stream.",
            "type": "TXT",
            "ttl": 3600,
            "changetype": "REPLACE",
            "records": [
                {
                    "content": '"v=DKIM1; h=sha256; k=rsa; t=y; s=email; p=XXXXXXXXXXXX"',
                    "disabled": False
                }
            ]
        }
    ]
}

r_delete_p = {
    "rrsets": [
        {
            "name": "352d079ffdaddd23edd407ff32a66c48._domainkey.s3bucket.stream.",
            "type": "TXT",
            "changetype": "DELETE"
        }
    ]
}

r_create_p = {
    "rrsets": [
        {
            "name": "352d079ffdaddd23edd407ff32a66c48._domainkey.s3bucket.stream.",
            "type": "TXT",
            "ttl": 3600,
            "changetype": "REPLACE",
            "records": [
                {
                    "content": '"v=DKIM1; h=sha256; k=rsa; t=y; s=email; p=YYYYYYYYYYYYYYY"',
                    "disabled": False
                }
            ]
        }
    ]
}

precord(r_delete_p)
precord(r_create_p)
#precord(r_replace_p)
precord_get()
