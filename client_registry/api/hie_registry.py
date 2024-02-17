import frappe
import json
import jwt
import numpy as np

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
	if not payload.get("related_to"):
		id_payload = dict(identity="{}:{}".format(payload.get("secret").lower(), payload.get("identification_number").lower()).replace(" ","_"))
		encoded_jwt = jwt.encode(id_payload, secret , algorithm="HS256")
		payload["id_hash"] = encoded_jwt
	doc = frappe.get_doc(payload)
	if other_ids:
		doc = update_other_ids(doc, other_ids)
	doc.save()
	# cd = doc.get_checkdigit(doc.get("name"))
	# frappe.rename_doc('Client Registry', doc.get("name"), '{}-{}'.format(doc.get("name"),cd))
	frappe.db.commit()
	return doc.to_fhir()
def update_other_ids(doc, other_ids):
    #Example:  [{'identification_type': 'Passport', 'identification_number': '64737838983'}]
    print("length: ",len(other_ids))
    docname = doc.get("name")
    filter_out_exists = list(filter(lambda x: not frappe.db.get_value("Client Identifier",dict(identification_type = x.get("identification_type"),identification_number = x.get("identification_number"), parent=docname), "name"),other_ids))
    count = 0
    for id_obj in filter_out_exists:
        count += 1
        print("Loop {}".format(count))
        doc.append("other_identifications",id_obj)
    return doc      
@frappe.whitelist()
def update_client(payload):#TBD
	doc = frappe.get_doc("Client Registry", payload.pop("id"))
	valid_keys = list(dict.fromkeys(doc.__dict__))
	keys = [x for x in list(dict.fromkeys(payload)) if x in valid_keys] #Don't send bogus keys, we won't bother. Is it a good idea?
	for k in keys:
		doc.set(k, payload[k])
	other_ids = payload.pop("other_identifications", None)
	dependants = payload.pop("dependants", None)
	if other_ids:
		doc = update_other_ids(doc, other_ids)
	if dependants:
		update_dependants_manually(doc, dependants)
	doc.save()
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
		# args = {
		# 	"first_name": dependant_doc.get("first_name"),
		# 	"middle_name": dependant_doc.get("middle_name") or "",
		# 	"last_name": dependant_doc.get("last_name"),
		# 	"gender": dependant_doc.get("gender"),
		# 	"relationship": _dependant.get("relationship"),
		# 	"identification_type": dependant_doc.get("identification_type"),
		# 	"identification_number": dependant_doc.get("identification_number"),
		# 	"linked_record": _dependant.get("id")
		# }
		# print("\n-",args)
		# doc.append("dependants", args)
	return doc.reload()
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
def base36encode(number):
	return np.base_repr(number, 36)
def fetch_based_on_other_identifiers(search_args):
    arg_keys = list(dict.fromkeys(search_args))
    print("Finding in other identifiers")
    docname = frappe.db.get_value("Client Identifier", search_args, "parent")
    if not docname: return []
    return frappe.get_all("Client Registry", filters=dict(name=docname), fields="*")
def _test_update_identifiers():
    other_ids=dict(identification_type="Birth Certificate", identification_number="27613716-234")
    to_update=dict(id="CR00000001", other_identifications=[other_ids])
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
    
        

	
	
	

	  