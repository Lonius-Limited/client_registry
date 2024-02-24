import frappe
import json
import jwt
import string, random, requests
from datetime import datetime

import urllib

N=4

# import numpy as np
@frappe.whitelist()
def client_lookup(payload, page_length=5):
	# payload = kwargs
	result = []
	if isinstance(payload, str):
		payload =json.loads(payload)
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
		result.append(doc.to_fhir())
	return dict(total=len(result), result=result)
@frappe.whitelist()
def client_lookup_nrb_search(payload, page_length=5):
	# payload = kwargs
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
	if (len(result)<1): return fetch_and_post_from_nrb(payload, encoded_pin)
	return dict(total=len(result), result=result)
def fetch_and_post_from_nrb(payload, encoded_pin=None, only_return_payload=1):
	#
	######
	
	if not encoded_pin: frappe.throw("Sorry, PIN is a required attribute to create a record in the client registry.")
	
	wt_secret = frappe.db.get_single_value("Client Registry Settings","security_hash")
 
	if not wt_secret: frappe.throw("Error: Critical security configuration is missing. Please contact the System Administrator")
	
	pin_number = jwt.decode(encoded_pin, wt_secret, algorithms=["HS256"])["pin_number"]

	##################
	if payload.get("identification_type") :
		nrb_data = nrb_by_id(identification_number=payload.get("identification_number"))
		if not nrb_data: return dict(total=0, result=[])
		if nrb_data.get("ErrorCode"): return dict(total=0, result=[])
		if not frappe.db.get_single_value("Client Registry Settings","automatically_create_client_from_nrb"):
			return dict(nrb_data=nrb_data)
		gender = "Female"
		if nrb_data.get("Gender") == "M" : gender ="Male"
		date_string = nrb_data.get("Date_of_Birth").split(" ")[0] 
		date_format = "%m/%d/%Y"
		dob = datetime.strptime(date_string, date_format)
		try:
			args = dict(
				doctype="Client Registry",
				first_name = nrb_data.get("First_Name"),
				last_name = nrb_data.get("Surname"),
				middle_name = nrb_data.get("Other_Name") or "",
				gender = gender,
				date_of_birth = dob,
				# civil_status = nrb_data.get(""),
				identification_type = payload.get("identification_type"),
				identification_number = payload.get("identification_number"),
				citizenship = nrb_data.get("Citizenship").upper(),
				place_of_birth = nrb_data.get("Place_of_Birth"),
				pin_number = pin_number
			)
			doc = frappe.get_doc(args).insert(ignore_permissions=1, ignore_mandatory=1)
			
			# doc.set("pin_number",pin_number)
			# doc.save()
			frappe.db.commit()
			doc.add_comment('Comment', text="{}".format(json.dumps(nrb_data)))
			return doc.to_fhir()
		except Exception as e:
			frappe.db.rollback()
			frappe.throw("{}".format(e))
			
		
	else:
		return dict(total=0, result=[])
		
	

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
@frappe.whitelist(allow_guest=1)    
def face_biometric_validation():
	files = frappe.request.files
	id = frappe.form_dict.id

	content = None
	
	urls_to_compare =[]
	for fn in [files['selfie'], files['id_front']]:
		content = fn.stream.read()
		filename = fn.filename
		ret = frappe.get_doc({
				"doctype": "File",
				"attached_to_doctype": 'Client Registry',#doctype,
				"attached_to_name": id,
				# "attached_to_field": fieldname,
				# "folder": folder,
				"file_name": filename,
				# "file_url": file_url,
				"is_private": 0,
				"content": content
			})
		ret.save(ignore_permissions=True)
		frappe.db.commit()
		d = frappe.get_doc("File", ret.get("name"))
		urls_to_compare.append(content)
	return image_comparison_aws_rekognition(urls_to_compare)
@frappe.whitelist()
def update_client(payload):#TBD
	# client_pin = payload.get("pin_number", None)
	# if not client_pin: frappe.throw("Please provide PIN number for this client inorder to update.")
	doc = frappe.get_doc("Client Registry", payload.pop("id"))
	# if doc.get_password("pin_number") != client_pin: frappe.throw("Invalid PIN, please reset and/or try again")
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
@frappe.whitelist()
def send_otp(*args, **kwargs):
	payload =  kwargs
	phone = ""
	if  "identification_type" in list(dict.fromkeys(payload)):
		phone = frappe.get_value("Client Registry",dict(identification_type=payload.get("identification_type"),identification_number=payload.get("identification_number")),"phone")
	else:
		phone = payload.get("phone")
	otp = ''.join(random.choices(string.digits, k=N))
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
	if not record.get("key")==otp.upper(): return dict(status="error", error_message="The token you provided is invalid or used.")
	record.db_set("valid",0, commit=True, update_modified=True)
	record.save(ignore_permissions=1)
	return dict(status="Valid")
@frappe.whitelist()
def nrb_by_id(*args, **kwargs):
	payload = kwargs
	id = payload["identification_number"]
	url = "https://neaims.go.ke/genapi/api/IPRS/GetPersonByID/{}".format(id)
	response = requests.get(url).json()
	return response
@frappe.whitelist(allow_guest=1)
def reset_pin(*args, **kwargs):
	wt_secret = frappe.db.get_single_value("Client Registry Settings","security_hash")
	if not wt_secret: frappe.throw("Error: Critical security configuration is missing. Please contact the System Administrator")
	payload = kwargs
	id = payload["id"]
	encoded_pin = payload["encoded_pin"]
	pin = jwt.decode(encoded_pin, wt_secret, algorithms=["HS256"])["pin_number"]
	doc = frappe.get_doc("Client Registry", id)
	doc.generate_pin(pin_number=pin)
def read_image(file_path):
	with open(file_path, "rb") as file:
		image_bytes = file.read()
	return image_bytes
@frappe.whitelist(allow_guest=1)
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
	return  dict(identification_number=re.search("B0(.*?)F",_match).group(1))
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
@frappe.whitelist(allow_guest=1)
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
@frappe.whitelist(allow_guest=1)
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
	
