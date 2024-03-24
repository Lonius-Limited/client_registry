import frappe
import json
import jwt
import string, random, requests
from datetime import datetime
from frappe import _
import urllib
from client_registry.api.nrb import NRB
N=4

# import numpy as np
@frappe.whitelist()
def client_lookup(payload, page_length=5):
	# payload = kwargs
	result = []
	if isinstance(payload, str):
		payload =json.loads(payload)
	#Star
	# page_length = payload.pop("page_length", 5)
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
		result.append(doc.to_fhir(unmask=1))
	return dict(total=len(result), result=result)
@frappe.whitelist()
def client_lookup_nrb_search(payload, page_length=5):	
	# files = frappe.request.files
	# docname = frappe.form_dict.id

	
	# payload = kwargs
	# {'identification_type': 'National ID',
	# 'identification_number': '27613716',
	# 'date_of_birth': '1990-05-02',
	# 'agent': 'SAFARICOM PLC-89204020',
	# 'encoded_pin': 'ew0KICAidHlwIjoiSldUIiwNCiAgImFsZyI6IkhTMjU2Ig0KfQ.ew0KICAicGluX251bWJlciI6IjE4NjYiDQp9.vo0YGIO-FUC4oD2px3XnK1ft1pTvsZHEe5dnmLET7l8'}
	result = []
	if isinstance(payload, str):
		payload =json.loads(payload)
	# page_length = payload.pop("page_length", 5)
	encoded_pin = payload.pop("encoded_pin", None)
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
			# records = fetch_based_on_other_identifiers(dict(identification_type=payload.get("identification_type"), identification_number=payload.get("identification_number"),))
			records = fetch_based_on_other_identifiers(dict(identification_type=payload.get("identification_type"), identification_number=payload.get("identification_number")))
	for record in records:
		doc = frappe.get_doc("Client Registry", record.get("name"))
		result.append(doc.to_fhir())
	if (len(result)<1):
		print("Searching In NRB Sources")
		return fetch_and_post_from_nrb(payload, encoded_pin, files=None)
	return dict(total=len(result), result=result)
def fetch_and_post_from_nrb(payload, encoded_pin=None, files=None):
	###Another check
	exists = frappe.db.get_value("Client Registry",dict(identification_number=payload.get("identification_number"),identification_type = payload.get("identification_type")),"name")
	if exists:
		doc = frappe.get_doc("Client Registry", exists)
		return doc.to_fhir()
	######
	if not payload.get("agent"): frappe.throw("Please provide your Agent ID provided during API onboarding")
	######
	
	if not encoded_pin: frappe.throw("Sorry, PIN is a required attribute to create a record in the client registry.")
	
	wt_secret = frappe.db.get_single_value("Client Registry Settings","security_hash")
 
	if not wt_secret: frappe.throw("Error: Critical security configuration is missing. Please contact the System Administrator")
	
	pin_number = jwt.decode(encoded_pin, wt_secret, algorithms=["HS256"])["pin_number"]

	##################
	if payload.get("identification_type") :
		# nrb_data = nrb_by_id(identification_number=payload.get("identification_number"))
		if payload.get("identification_type") in ["citizen","alien","refugee"]:
			n = NRB(pin_number, **payload)
			return n.create_client()
		nrb_data = nrb_by_dynamic_id(**payload)
		if not nrb_data: return dict(total=0, result=[])
		if nrb_data.ErrorCode: return dict(total=0, result=[])
		print(nrb_data.ErrorCode)
		if not frappe.db.get_single_value("Client Registry Settings","automatically_create_client_from_nrb"):
			return dict(nrb_data=nrb_data)
		gender = "Female"
		if nrb_data.Gender == "M" : gender ="Male"
		date_string = nrb_data.Date_of_Birth.split(" ")[0] 
		date_format = "%m/%d/%Y"
		dob = datetime.strptime(date_string, date_format)
		print(payload.get("date_of_birth"))
		if payload.get("date_of_birth"):
			print("Comparing {} and {}".format(payload.get("date_of_birth"),str(dob).split(" ")[0]))
			if 	payload.get("date_of_birth") != str(dob).split(" ")[0]:
				frappe.throw("The provided date of birth does not match the date of birth in the persons registry database.")
		try:
			args = dict(
				doctype="Client Registry",
				first_name = nrb_data.First_Name,
				last_name = nrb_data.Surname,
				middle_name = nrb_data.Other_Name or "",
				gender = gender,
				date_of_birth = dob,
				# civil_status = nrb_data.get(""),
				identification_residence = nrb_data.Place_of_Live or None,
				identification_type = payload.get("identification_type"),
				identification_number = payload.get("identification_number"),
				citizenship = nrb_data.Citizenship.upper(),
				place_of_birth = nrb_data.Place_of_Birth,
				pin_number = pin_number,
				agent = payload.get("agent")
			)
			doc = frappe.get_doc(args).insert(ignore_permissions=1, ignore_mandatory=1)
			if files:
				selfie_obj = files['selfie']
				selfie_content = selfie_obj.stream.read()
				selfie_filename = selfie_obj.filename
				selfie_ret = frappe.get_doc({
						"doctype": "File",
						"attached_to_doctype": 'Client Registry',#doctype,
						"attached_to_name": doc.get("name"),
						# "attached_to_field": "client_passport_photo",
						# "folder": folder,
						"file_name": selfie_filename,
						# "file_url": file_url,
						"is_private": 0,
						"content": selfie_content
					})
				selfie_ret.save(ignore_permissions=True)
				frappe.db.commit()
			frappe.db.commit()
			doc.add_comment('Comment', text="{}".format(nrb_data.__dict__))
			return doc.to_fhir()
		except Exception as e:
			print("{}".format(e))
			frappe.db.rollback()
			exists = frappe.db.get_value("Client Registry",dict(identification_number=payload.get("identification_number"),identification_type = payload.get("identification_type")),"name")
			if exists:
				doc = frappe.get_doc("Client Registry", exists)
				return doc.to_fhir()
			return dict(error="{}".format(e))
			# frappe.throw("{}".format(e))
			
		
	else:
		return dict(total=0, result=[])
		
# def insert_nrb_data(nrb_args):
#     pass	

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
	# pin_number = payload.pop("pin_number", None)
	# if not pin_number: frappe.throw("Sorry, PIN is a required attribute to create a record in the client registry.")
	payload["doctype"] ="Client Registry"
	resource_type = payload.pop("resourceType")
	identifiers =  payload.pop("originSystem")
	payload["registry_system"] = identifiers.get("system") or ""
	
	payload["facility_code"] = identifiers.get("facility_code") or ""
	other_ids = payload.pop("other_identifications", None)
	doc = frappe.get_doc(payload)
	if other_ids:
		for id_obj in other_ids:
			doc.append("other_identifications",id_obj)
	doc.save()
	# if 
	frappe.db.commit()
	return doc.to_fhir()
@frappe.whitelist()
def face_biometrics_no_id():
	files = frappe.request.files
	docname = frappe.form_dict.id
	obj = files['selfie']
	_context_doc_1 = None
	# if docname:
	_context_doc_1 = frappe.get_doc("Client Registry", docname)
	selfie_content = obj.stream.read()
	selfie_filename = obj.filename
	selfie_ret = frappe.get_doc({
			"doctype": "File",
			"attached_to_doctype": 'Client Registry',#doctype,
			"attached_to_name": docname,
			# "attached_to_field": "client_passport_photo",
			# "folder": folder,
			"file_name": selfie_filename,
			# "file_url": file_url,
			"is_private": 0,
			"content": selfie_content
		})
	selfie_ret.save(ignore_permissions=True)
@frappe.whitelist()    
def face_biometric_validation():
	files = frappe.request.files
	docname = frappe.form_dict.id

	content = None
	doc = None

	# if docname:
	doc = frappe.get_doc("Client Registry", docname) #Must be provided
	
	urls_to_compare =[]
	# for fn in [files['selfie'], files['id_front']]:
	def _upload_passport_selfie(selfie_obj):
		# selfie_obj = files['selfie']
		_context_doc_1 = None
		# if docname:
		_context_doc_1 = frappe.get_doc("Client Registry", docname)
		selfie_content = selfie_obj.stream.read()
		selfie_filename = selfie_obj.filename
		selfie_ret = frappe.get_doc({
				"doctype": "File",
				"attached_to_doctype": 'Client Registry',#doctype,
				"attached_to_name": docname,
				# "attached_to_field": "client_passport_photo",
				# "folder": folder,
				"file_name": selfie_filename,
				# "file_url": file_url,
				"is_private": 0,
				"content": selfie_content
			})
		selfie_ret.save(ignore_permissions=True)
		
		d = frappe.get_doc("File", selfie_ret.get("name"))
		# if count == 0:
		# if docname:
		_context_doc_1.db_set("client_passport_photo", d.get("file_url"),commit=True)
		_context_doc_1.add_comment('Comment', text="PASSPORT {}".format(d.get("file_url")))
		urls_to_compare.append(selfie_content)
		frappe.db.commit()
 ##################################ADDING THE ID#####################################
	def _upload_photo_id(id_obj):
		# id_obj = files['id_front']
		_context_doc = frappe.get_doc("Client Registry", docname)
		id_content = id_obj.stream.read()
		id_filename = id_obj.filename
		id_ret = frappe.get_doc({
				"doctype": "File",
				"attached_to_doctype": 'Client Registry',#doctype,
				"attached_to_name": docname,
				# "attached_to_field": "client_identifier_photo_id",
				# "folder": folder,
				"file_name": id_filename,
				# "file_url": file_url,
				"is_private": 0,
				"content": id_content
			})
		id_ret.save(ignore_permissions=True)
		
		_d = frappe.get_doc("File", id_ret.get("name"))
		_context_doc.db_set("client_identifier_photo_id", _d.get("file_url"),commit=True)
		_context_doc.add_comment('Comment', text="PHOTO ID {}".format(_d.get("file_url")))
		urls_to_compare.append(id_content)
		frappe.db.commit()
	##################################ADDING THE FINGERPRINT LEFT THUMB#####################################
	def _upload_fingerprint_left_thumb(fingerprint_obj):
		# id_obj = files['id_front']
		_context_doc = frappe.get_doc("Client Registry", docname)
		fingerprint_content = fingerprint_obj.stream.read()
		fingerprint_filename = fingerprint_obj.filename
		fingerprint_ret = frappe.get_doc({
				"doctype": "File",
				"attached_to_doctype": 'Client Registry',#doctype,
				"attached_to_name": docname,
				# "attached_to_field": "client_identifier_photo_id",
				# "folder": folder,
				"file_name": fingerprint_filename,
				# "file_url": file_url,
				"is_private": 0,
				"content": fingerprint_content
			})
		fingerprint_ret.save(ignore_permissions=True)
		
		_f = frappe.get_doc("File", fingerprint_ret.get("name"))
		_context_doc.db_set("fingerprint_left_thumb", _f.get("file_url"),commit=True)
		_context_doc.add_comment('Comment', text="Fingerprint Left Thumb {}".format(_f.get("file_url")))
		urls_to_compare.append(fingerprint_content)
		frappe.db.commit()
	_upload_photo_id(files['id_front'])
	_upload_passport_selfie(files['selfie'])
	_upload_fingerprint_left_thumb(files['fingerprint_left_thumb'])
	doc.image_rekognition_match()
	frappe.db.commit()
	# doc.reload()
	return frappe.get_doc("Client Registry",docname).to_fhir()
	# return image_comparison_aws_rekognition(urls_to_compare)

@frappe.whitelist(allow_guest=1)
def update_client(payload):#TBD-->Make sure encoded_pin is (*args, **kwargs))
	if isinstance(payload, str):
		payload =json.loads(payload)
	# ==================================================================
	encoded_pin = payload.pop("encoded_pin", None)
 
	if not encoded_pin: frappe.throw("Client PIN is required for this client inorder to update this record.")
 
	wt_secret = frappe.db.get_single_value("Client Registry Settings","security_hash")
 
	if not wt_secret: frappe.throw("Error: Critical security configuration is missing. Please contact the System Administrator")
	
	pin_number = jwt.decode(encoded_pin, wt_secret, algorithms=["HS256"])["pin_number"]

	# #=====================================================================
	docname = payload.pop("id")
 
	doc = frappe.get_doc("Client Registry", docname)
 
	if not doc.validate_pin(pin_number) : frappe.throw("Invalid PIN, please reset and/or try again")
 
	#=====================================================================
	valid_keys = list(dict.fromkeys(doc.__dict__))
	#Second Check--> are the fields blacklisted?
	fields = frappe.get_doc("Client Registry Settings").get("blacklisted_fields")
	blacklisted_fields = list(filter(lambda x: x.blacklisted==1, fields))
	blacklisted_fieldnames =[x.get("field_name") for x in blacklisted_fields]
	#-->End second check
	keys = [x for x in list(dict.fromkeys(payload)) if x in valid_keys and x not in blacklisted_fieldnames] #Don't send bogus keys, we won't bother. Is it a good idea?
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
@frappe.whitelist()
def update_client_v2(payload):#TBD
	encoded_pin = payload.get("encoded_pin", None)
	if not encoded_pin: frappe.throw("Please provide PIN number for this client inorder to update.")
 
	wt_secret = frappe.db.get_single_value("Client Registry Settings","security_hash")
 
	if not wt_secret: frappe.throw("Error: Critical security configuration is missing. Please contact the System Administrator")
	
	pin_number = jwt.decode(encoded_pin, wt_secret, algorithms=["HS256"])["pin_number"]
 
	doc = frappe.get_doc("Client Registry", payload.pop("id"))
 
	if doc.get_password("pin_number") != pin_number: frappe.throw("Invalid PIN, please reset and/or try again")
 
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
		return dict(status="error",error_desc="Invalid resource type")
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
def validate_pin(payload):
	encoded_pin = payload.pop('encoded_pin')
	wt_secret = frappe.db.get_single_value("Client Registry Settings","security_hash")
	if not wt_secret: frappe.throw("Error: Critical security configuration is missing. Please contact the System Administrator")
	pin = jwt.decode(encoded_pin, wt_secret, algorithms=["HS256"])["pin_number"]
	docname = frappe.get_value("Client Registry",payload,'name')
	return frappe.get_doc("Client Registry", docname).validate_pin(pin)

@frappe.whitelist()
def send_otp(*args, **kwargs):
	payload =  kwargs
	# #

	# wt_secret = frappe.db.get_single_value("Client Registry Settings","security_hash")
	# if not wt_secret: frappe.throw("Error: Critical security configuration is missing. Please contact the System Administrator")
	# encoded_pin = payload["encoded_pin"]
	# pin = jwt.decode(encoded_pin, wt_secret, algorithms=["HS256"])["pin_number"]
	# #
	phone = payload.get("phone", None)
	email = payload.get("email", None)
	
	if  "identification_type" in list(dict.fromkeys(payload)):
		if "encoded_pin" in list(dict.fromkeys(payload)): 
			if not validate_pin(payload): frappe.throw("Sorry, Invalid Pin")
		phone, email = frappe.get_value("Client Registry",dict(identification_type=payload.get("identification_type"),identification_number=payload.get("identification_number")),["phone","email"])
	otp = ''.join(random.choices(string.digits, k=N))
	args = dict(doctype="OTP Record",key=otp, valid=1,phone=phone, email=email)
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
	if not record.get("key")==otp.upper(): return dict(status="error", error_message="The token you provided is invalid or used.")
	record.db_set("valid",0, commit=True, update_modified=True)
	record.save(ignore_permissions=1)
	return dict(status="Valid")
@frappe.whitelist()
def nrb_by_dynamic_id(*args, **kwargs):#IPRS btw
	payload = kwargs
	from iprs import IPRS
	identification_type, id = payload.get("identification_type"), payload.get("identification_number")
	identification_type_doc = frappe.get_doc("Identification Type",identification_type)
	soap_method = identification_type_doc.get("iprs_soap_method")
	soap_query_field = identification_type_doc.get("iprs_soap_query_field")
	if not (soap_query_field or soap_method): frappe.throw("IPRS Configurations not done on the Identification Document type")
	q_args = dict(query_type=soap_method)
	q_args[soap_query_field] = id
	# frappe.throw("{}".format(q_args))
	return IPRS(**q_args).query_iprs()
@frappe.whitelist()
def nemis_my_kids_by_id(*args, **kwargs):
	payload = kwargs
	cr_id = payload.get("id")
	doc_exists = frappe.db.get_value("Client Registry",cr_id, "name")
	if not doc_exists: frappe.throw(f"Sorry, this Client Registry ID does not exist: {cr_id}")
	national_id = frappe.db.get_value("Client Registry",doc_exists,"identification_number")
	url = 'http://nemis.education.go.ke/generic2/api/Learner/MyChildren/{}'.format(national_id)
	cr_settings = frappe.get_doc("Client Registry Settings")
	response = requests.get(url, auth=(cr_settings.get("neamis_username"), cr_settings.get_password("neamis_password"))).json()
	fhir_response = dict(total=len(response or []))
	fhir_records= []
	if response:
		for nrb_data in response:
			gender = "Female"
			if nrb_data.get("gender") == "M" : gender ="Male"
			date_string = nrb_data.get("dob").split(" ")[0] 
			date_format = "%d-%m-%Y"
			dob = datetime.strptime(date_string, date_format)
			exists =  frappe.db.get_value("Client Registry", dict(identification_type="Birth Certificate", identification_number=nrb_data.get("birth_Cert_No")),"name")
			relationship = "Mother" #The most likely to gethere first
			if national_id == nrb_data.get("father_IDNo"): relationship = "Father"
			if national_id == nrb_data.get("guardian_IDNo"): relationship = "Guardian"
			if exists:
				_doc = frappe.get_doc("Client Registry", exists)
				fhir_records.append(_doc.to_fhir())
				continue
			try:
				args = dict(
					doctype="Client Registry",
					first_name = nrb_data.get("firstName"),
					last_name = nrb_data.get("surname"),
					middle_name = nrb_data.get("otherName") or "",
					gender = gender,
					date_of_birth = dob,
					identification_type = "Birth Certificate",
					identification_number = nrb_data.get("birth_Cert_No"),
					citizenship = "KENYAN" if  nrb_data.get("nationality") == "1" else None,
					# latitude = nrb_data.get("latitude"),
					# longitude = nrb_data.get("longitude"),
					county = nrb_data.get("county_Name"),
					sub_county = nrb_data.get("sub_County_Name"),
					phone= nrb_data.get("tel_Number") or nrb_data.get("mobile_Number1"),
					email = nrb_data.get("email_Address"),
					related_to = cr_id,
					relationship = relationship,
					agent = payload.get("agent")
				)
				doc = frappe.get_doc(args).insert(ignore_permissions=1, ignore_mandatory=1)
				frappe.db.commit()
				doc.add_comment('Comment', text="{}".format(json.dumps(nrb_data)))
				frappe.db.commit()
				fhir_records.append(doc.to_fhir())
				# return doc.to_fhir()
			except Exception as e:
				frappe.throw("{}".format(e))
				return dict(error="{}".format(e))
	fhir_response["result"] = fhir_records
	return fhir_response
@frappe.whitelist()
def nrb_by_id(*args, **kwargs):
	payload = kwargs
	id = payload["identification_number"]
	url = "https://neaims.go.ke/genapi/api/IPRS/GetPersonByID/{}".format(id)
	response = requests.get(url).json()
	return response
@frappe.whitelist()
def reset_pin(*args, **kwargs):
	wt_secret = frappe.db.get_single_value("Client Registry Settings","security_hash")
	if not wt_secret: frappe.throw("Error: Critical security configuration is missing. Please contact the System Administrator")
	payload = kwargs
	id = payload["id"]
	encoded_pin = payload["encoded_pin"]
	pin = jwt.decode(encoded_pin, wt_secret, algorithms=["HS256"])["pin_number"]
	# if "phone" in list(dict.fromkeys(payload)):
	# 	frappe.db.set_value("Client Registry", id, "phone", payload["phone"], update_modified=True)
	# 	frappe.db.commit()
	doc = frappe.get_doc("Client Registry", id)
	doc.generate_pin(pin_number=pin)
	if "phone" in list(dict.fromkeys(payload)):
		doc.update_phone(payload["phone"])
	# if "phone" in list(dict.fromkeys(payload)):
	# 	doc.update_phone(payload["phone"])
def read_image(file_path):
	with open(file_path, "rb") as file:
		image_bytes = file.read()
	return image_bytes
@frappe.whitelist()
def image_comparison_aws_rekognition(files):#Array of two s3 sources
	import boto3
	import urllib.parse
	import requests
	sourceFile, targetFile = files[0] , files[1]
	# return sourceFile, targetFile
	AWS_SETTINGS = frappe.get_doc("S3 File Attachment")
	_REKOGNITION_CLIENT = boto3.client(
		'rekognition',
		aws_access_key_id=AWS_SETTINGS.get("aws_key"), #"",
		aws_secret_access_key=AWS_SETTINGS.get("aws_secret"), # "",
		# aws_session_token=SESSION_TOKEN
		region_name=AWS_SETTINGS.get("region_name") #""
	)
	bucket_name = AWS_SETTINGS.get("bucket_name")
	# imageSource = open(requests.utils.requote_uri(sourceFile), 'rb')
	# imageTarget = open(requests.utils.requote_uri(targetFile), 'rb')
	imageSource = sourceFile
	imageTarget = targetFile
 
	# response = _REKOGNITION_CLIENT.compare_faces(SimilarityThreshold=90,
	# 								SourceImage={"S3Object": {
	#         "Bucket": bucket_name,
	#         "Name": sourceFile.rpartition("/"[-1])[2]
	#     }},
	# 								TargetImage={"S3Object": {
	#         "Bucket": bucket_name,
	#         "Name": targetFile.rpartition("/"[-1])[2]
	#     }}) 
	# return type(imageTarget)

	response = _REKOGNITION_CLIENT.compare_faces(SimilarityThreshold=90,
									SourceImage={'Bytes': imageSource},
									TargetImage={'Bytes': imageTarget}) 
	return response
@frappe.whitelist()
def document_extract(filename=None, _file_bytes=None):	
	import boto3
	AWS_SETTINGS = frappe.get_doc("S3 File Attachment")
	_TEXTRACT_CLIENT = boto3.client(
		'textract',
		aws_access_key_id=AWS_SETTINGS.get("aws_key"), #"",
		aws_secret_access_key=AWS_SETTINGS.get("aws_secret"), # "",
		region_name=AWS_SETTINGS.get("region_name") #""
	)
	
	randomfilename=''.join(random.choices( string.digits, k=10))
	if filename:	# print(client.__dict__)
		urllib.request.urlretrieve(filename, "{}.png".format(randomfilename))
	file_bytes= _file_bytes or read_image("{}.png".format(randomfilename))
	response = _TEXTRACT_CLIENT.detect_document_text(
		Document=
			{
				'Bytes':file_bytes,
		
			},
		
	)
	import re
	blocks = list(filter(lambda x: x.get("BlockType")=="LINE",response.get("Blocks")))
	f = list(map(lambda x: x["Text"],blocks))
	id = list(filter(lambda y: re.search("B0(.*?)F",y), f))
	if not id: return ""
	_match =  id[0]
	return  dict(identification_number=re.search("B0(.*?)[A-Z]",_match).group(1))
	# id_regex =  re.search("^B0 & F$",y) #^B0[^BF]*F$
 	# print(response)
	# return f, id
def image_matching(filename1, filename2):
	# return filename2, filename1
	try:
		import face_recognition

		picture_of_me = face_recognition.load_image_file(filename1)
		my_face_encoding = face_recognition.face_encodings(picture_of_me)[0]

		# my_face_encoding now contains a universal 'encoding' of my facial features that can be compared to any other picture of a face!

		unknown_picture = face_recognition.load_image_file(filename2)
		unknown_face_encoding = face_recognition.face_encodings(unknown_picture)[0]

		# Now we can see the two face encodings are of the same person with `compare_faces`!

		return my_face_encoding,unknown_face_encoding
		results = face_recognition.compare_faces([my_face_encoding], unknown_face_encoding)

		return results[0]
	except Exception as e:
		frappe.throw("{}".format(e))
@frappe.whitelist()
def extract_identification_number_from_id_scan():
	files = frappe.request.files
	# for file in files:
	content = None
	if 'file' in files:
		file = files['file']
		content = file.stream.read()
		filename = file.filename

	frappe.local.uploaded_file = content
	frappe.local.uploaded_filename = filename
	return document_extract(filename=None, _file_bytes=content)
@frappe.whitelist()
def match_images_from_upload():
	files = frappe.request.files
	
 
	content = None
	
	urls_to_compare =[]
	for fn in [files['filename1'], files['filename2']]:
		content = fn.stream.read()
		filename = fn.filename
		ret = frappe.get_doc({
				"doctype": "File",
				# "attached_to_doctype": 'Client Registry',#doctype,
				# "attached_to_name": doc.get("name"),
				# "attached_to_field": fieldname,
				# "folder": folder,
				"file_name": filename,
				# "file_url": file_url,
				"is_private": 0,
				"content": content
			})
		ret.save(ignore_permissions=True)
		frappe.db.commit()
		randomfilename=''.join(random.choices( string.digits, k=10))
		urllib.request.urlretrieve(ret.get("file_url"),"{}.jpg".format(randomfilename))
		urls_to_compare.append("{}.jpg".format(randomfilename))
	
	# return 

	
	return image_matching(urls_to_compare[0], urls_to_compare[1])
	# frappe.local.uploaded_file = content
	# frappe.local.uploaded_filename = filename
	
