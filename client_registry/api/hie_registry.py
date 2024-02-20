import frappe
import json
import jwt
import string, random
N=4
# import numpy as np

@frappe.whitelist()
def client_lookup(payload, page_length=5):
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
	if not records:
		arg_keys = list(dict.fromkeys(payload))
		if "identification_type" in arg_keys and "identification_number" in arg_keys:
			records = fetch_based_on_other_identifiers(dict(identification_type=payload.get("identification_type"), identification_number=payload.get("identification_number")))
	for record in records:
		doc = frappe.get_doc("Client Registry", record.get("name"))
		result.append(doc.to_fhir())
	return dict(total=len(result), result=result)
@frappe.whitelist()
def client_nrb_lookup(payload, page_length=5):
	result = []
	if isinstance(payload, str):
		payload =json.loads(payload)
	or_filters = payload
	filters_from_user =  list(dict.fromkeys(or_filters))
	if(len(filters_from_user)<1): return dict(status="error",description="Search filters not provided")
	if "id" in filters_from_user:
		or_filters["name"] = payload.pop("id")
	# return frappe.get_all("Client Registry", or_filters=or_filters, fields=["first_name","middle_name","last_name","full_name","gender","date_of_birth","identification_type","identification_number","is_alive","deceased_datetime","phone","email","country","county","sub_county","ward","village","related_to","related_to_full_name"])
	records = frappe.get_all("NRB Record",filters=or_filters, page_length=page_length)
	# return []
	# if not records:
	# 	arg_keys = list(dict.fromkeys(payload))
	# 	if "identification_type" in arg_keys and "identification_number" in arg_keys:
	# 		records = fetch_based_on_other_identifiers(dict(identification_type=payload.get("identification_type"), identification_number=payload.get("identification_number")))
	# for record in records:
	# 	doc = frappe.get_doc("NRB Record", record.get("name"))
	# 	result.append(doc.to_fhir())
	return dict(total=len(result), result=result)
@frappe.whitelist()
def create_client(payload):
	# return type(payload)
	if isinstance(payload, str):
		payload =json.loads(payload)
	payload["doctype"] ="Client Registry"
	resource_type = payload.pop("resourceType")
	identifiers =  payload.pop("originSystem")
	payload["registry_system"] = identifiers.get("system") or ""
	last_name = payload["last_name"]
	date_of_birth = payload["date_of_birth"]
	payload["facility_code"] = identifiers.get("facility_code") or ""
	secret = "{}:{}".format(last_name,date_of_birth)
	other_ids = payload.pop("other_identifications", None)
	# if not payload.get("related_to"):
	# 	id_payload = dict(identity="{}:{}".format(payload.get("identification_type").lower(), payload.get("identification_number").lower()).replace(" ","_"))
	# 	encoded_jwt = jwt.encode(id_payload, secret , algorithm="HS256")
	# 	payload["id_hash"] = encoded_jwt[:140]
	# 	payload["full_hash"] = encoded_jwt
	doc = frappe.get_doc(payload)
	if other_ids:
		for id_obj in other_ids:
			doc.append("other_identifications",id_obj)
	doc.save()
	# cd = doc.get_checkdigit(doc.get("name"))
	# frappe.rename_doc('Client Registry', doc.get("name"), '{}-{}'.format(doc.get("name"),cd))
	frappe.db.commit()
	return doc.to_fhir()    
@frappe.whitelist()
def update_client(payload):#TBD
	doc = frappe.get_doc("Client Registry", payload.pop("id"))
	valid_keys = list(dict.fromkeys(doc.__dict__))
	keys = [x for x in list(dict.fromkeys(payload)) if x in valid_keys] #Don't send bogus keys, we won't bother. Is it a good idea?
	for k in keys:
		doc.set(k, payload[k])
	other_ids = payload.pop("other_identifications", None)
	dependants = payload.pop("dependants", None)
	doc.save()
	if other_ids:
		print("\nPreparing to enter ==> {} records".format(len(other_ids)))
		for id_obj in other_ids:
			doc.append("other_identification_docs",id_obj)
		doc.save()
		doc.reload()
	if dependants:
		update_dependants_manually(doc, dependants)
		doc.reload()
	frappe.db.commit()
	return doc.to_fhir()
def validate_resource_type(resource):
	if not resource.get("Patient"):
		return dict(status="error",error_desc="Invalid resource")
def update_dependants_manually(doc, dependants):
	docname = doc.get("name")
	filter_out_exists = list(filter(lambda x: not frappe.db.get_value("Dependants",dict(linked_record = x.get("id"), parent=docname), "name"),dependants))
	for _dependant in filter_out_exists:
		dependant_doc = frappe.get_doc("Client Registry", _dependant.get("id"))
		dependant_doc.related_to = docname
		dependant_doc.relationship = _dependant.get("relationship")
		dependant_doc.save()
	return doc.reload()
# def update_dependants(doc, state):
# 	if not doc.get("related_to"): return
# 	is_dependant_of_doc = frappe.get_doc("Client Registry",doc.get("related_to"))
# 	# if (is_dependant_of_doc.get("related_to")==doc.get("name")): frappe.throw("Sorry, cyclic dependency detected.")
# 	client_dependants = is_dependant_of_doc.get("dependants")
# 	records = [x.get("linked_record") for x in client_dependants]
# 	if doc.get("name") in records: return
# 	is_dependant_of_doc.append("dependants", {
# 		"first_name": doc.get("first_name"),
# 		"middle_name": doc.get("middle_name") or "",
# 		"last_name": doc.get("last_name"),
# 		"gender": doc.get("gender"),
# 		"relationship": doc.get("relationship"),
# 		"identification_type": doc.get("identification_type"),
# 		"identification_number": doc.get("identification_number"),
# 		"linked_record": doc.get("name")
# 	})
# 	is_dependant_of_doc.save()
def update_full_name(doc, state):
	full_name = "{} {} {}".format(doc.get("first_name"),doc.get("middle_name") or "",doc.get("last_name"))
	doc.set("full_name", full_name)
def base36encode(number):
	return np.base_repr(number, 36)
def fetch_based_on_other_identifiers(search_args):
	arg_keys = list(dict.fromkeys(search_args))
	print("Finding in other identifiers")
	docname = frappe.db.get_value("Client Identifier", search_args, "parent")
	if not docname: return []
	return frappe.get_all("Client Registry", filters=dict(name=docname), fields="*")
def _test_update_identifiers():
	_other_ids=dict(identification_type="Passport", identification_number="Z7A234")
	to_update=dict(id="UPI-64557-2023-000002", other_identifications=[_other_ids])
	print("Sending,===>", to_update)
	update_client(to_update)
def _test_manually_add_dependants():
	upis =["UPI-64557-2023-000002","UPI-15706-2023-000007-3"]
	dependants = []
	for upi in upis:
		dependants.append(dict(id=upi,relationship="Son"))
	to_update=dict(id="CR00000001", dependants=dependants)
	print("Sending,===>", to_update)
	update_client(to_update)
@frappe.whitelist()
def send_otp(*args, **kwargs):
	payload =  kwargs
	phone = payload.get("phone")
	otp = ''.join(random.choices(string.ascii_uppercase + string.digits, k=N))
	args = dict(doctype="OTP Record",key=otp, valid=1,phone=phone)
	doc = frappe.get_doc(args).save(ignore_permissions=True)
	frappe.db.commit()
	return dict(otp_record=doc.get("name"))
@frappe.whitelist()
def validate_otp(*args, **kwargs):
	payload = kwargs
	otp_record  = payload.get("otp_record")
	otp = payload.get("otp")
	record = frappe.get_doc("OTP Record", otp_record)
	if not record.get("valid"): return dict(status="error", error_message="The token you provided is already used.")
	if not record.get("key")==otp.upper(): return dict(status="error", error_message="The token you provided is invalid or used")
	record.db_set("valid",0, commit=True, update_modified=True)
	record.save(ignore_permissions=1)
	return dict(status="Valid")
	
	

	  