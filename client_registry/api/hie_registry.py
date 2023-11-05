import frappe
import json
import jwt


@frappe.whitelist()
def client_lookup(payload, page_length=20):
	result = []
	if isinstance(payload, str):
		payload =json.loads(payload)
	or_filters = payload
	filters_from_user =  list(dict.fromkeys(or_filters))
	if(len(filters_from_user)<1): return dict(status="error",description="Search filters not provided")
	if "id" in filters_from_user:
		or_filters["name"] = payload.pop("id")
	# return frappe.get_all("Client Registry", or_filters=or_filters, fields=["first_name","middle_name","last_name","full_name","gender","date_of_birth","identification_type","identification_number","is_alive","deceased_datetime","phone","email","country","county","sub_county","ward","village","related_to","related_to_full_name"])
	records = frappe.get_all("Client Registry",filters=or_filters, page_length=page_length)
	for record in records:
		doc = frappe.get_doc("Client Registry", record.get("name"))
		result.append(doc.to_fhir())
	return dict(total=len(result), result=result)
@frappe.whitelist()
def create_client(payload):
	# return type(payload)
	if isinstance(payload, str):
		payload =json.loads(payload)
	payload["doctype"] ="Client Registry"
	payload.pop("resourceType")
	identifiers =  payload.pop("originSystem")
	payload["registry_system"] = identifiers.get("system") or ""
	payload["facility_code"] = identifiers.get("facility_code") or ""
	if not payload.get("related_to"):
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
def update_dependants(doc, state):
	if not doc.get("related_to"): return
	is_dependant_of_doc = frappe.get_doc("Client Registry",doc.get("related_to"))
	# if (is_dependant_of_doc.get("related_to")==doc.get("name")): frappe.throw("Sorry, cyclic dependency detected.")
	client_dependants = is_dependant_of_doc.get("dependants")
	records = [x.get("linked_record") for x in client_dependants]
	if doc.get("name") in records: return
	is_dependant_of_doc.append("dependants", {
		"first_name": doc.get("first_name"),
		"middle_name": doc.get("middle_name") or "",
		"last_name": doc.get("last_name"),
		"gender": doc.get("gender"),
		"relationship": doc.get("relationship"),
		"identification_type": doc.get("identification_type"),
		"identification_number": doc.get("identification_number"),
		"linked_record": doc.get("name")
	})
	is_dependant_of_doc.save()
def update_full_name(doc, state):
	full_name = "{} {} {}".format(doc.get("first_name"),doc.get("middle_name") or "",doc.get("last_name"))
	doc.set("full_name", full_name)

	
	
	

	  