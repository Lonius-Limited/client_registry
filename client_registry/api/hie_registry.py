import frappe
import json
import jwt


@frappe.whitelist()
def patient_lookup(payload, page_length=20):
	result = []
	if isinstance(payload, str):
		payload =json.loads(payload)
	or_filters = payload
	filters_from_user =  list(dict.fromkeys(or_filters))
	if(len(filters_from_user)<1): return dict(status="error",description="Search filters not provided")
	# return frappe.get_all("Client Registry", or_filters=or_filters, fields=["first_name","middle_name","last_name","full_name","gender","date_of_birth","identification_type","identification_number","is_alive","deceased_datetime","phone","email","country","county","sub_county","ward","village","related_to","related_to_full_name"])
	records = frappe.get_all("Client Registry",filters=or_filters, page_length=page_length)
	for record in records:
		doc = frappe.get_doc("Client Registry", record.get("name"))
		result.append(doc.to_fhir())
	return result
@frappe.whitelist()
def create_patient(payload):
	# return type(payload)
	if isinstance(payload, str):
		payload =json.loads(payload)
	payload["doctype"] ="Client Registry"
	payload.pop("resourceType")
	identifiers =  payload.pop("identifier")
	payload["registry_system"] = identifiers.get("system") or ""
	payload["record_id"] = identifiers.get("value") or ""
	id_payload = dict(identity="{}:{}".format(payload.get("identification_type").lower(), payload.get("identification_number").lower()).replace(" ","_"))
	encoded_jwt = jwt.encode(id_payload, "secret", algorithm="HS256")
	payload["id_hash"] = encoded_jwt
	doc = frappe.get_doc(payload).insert()
	frappe.db.commit()
	return doc.to_fhir()
@frappe.whitelist()
def update_patient(payload):#TBD
	args = frappe.get_all("Client Registry", payload.get("id"))
def validate_resource_type(resource):
	if not resource.get("Patient"):
		return dict(status="error",error_desc="Invalid resource")
	# "dependants":[
	#     "first_name":,
	#     "middle_name",
	#     "last_name",
	#     "gender",
	#     "relation",
	#     "linked_record"
	# ]  