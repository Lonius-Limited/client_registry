import frappe, requests
from datetime import datetime
@frappe.whitelist()
def validate_phone_and_id(*args, **kwargs):
    payload = kwargs
    settings = frappe.get_doc("Client Registry Settings")
    token = get_token(settings).get("access_token")
    print(token)
    validate_url = settings.get("validate_url")
    headers = dict(Authorization="Bearer {}".format(token))
    data =  kyc_payload(settings,payload)
    response = requests.post(validate_url, headers=headers, json=data)
    return response.json()
def get_token(settings):
    token_url, token_user, token_pass = settings.get("token_url"), settings.get("token_username"), settings.get_password("token_password")
    response = requests.post(token_url, auth=(token_user, token_pass))
    return response.json()
def get_curr_timestamp_int():
    curr_dt = datetime.now()
    timestamp = int(round(curr_dt.timestamp()))
    return timestamp
def kyc_payload(settings, payload):
    return {
        "requestRefID": "{}".format(get_curr_timestamp_int()),
        "shortCode": settings.get("validate_shortcode") or "12345",
        "msisdn": payload.get("msisdn") or "254710860780",
        "idType": payload.get("idType")  or "01",
        "idNumber": payload.get("idNumber")  or "454353453"
    } 