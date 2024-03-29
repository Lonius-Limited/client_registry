# Copyright (c) 2022, Lonius Limited and contributors
# For license information, please see license.txt

import frappe, jwt, random, string, africastalking
from frappe.model.document import Document
from frappe import _
from client_registry.api.nrb import NRB
N = 4


class ClientRegistry(Document):
	def _get_api_key(self):
		return frappe.db.get_single_value("Client Registry Settings","africastalking_sms_api")
	def initialize_sms_provider(self):
		africastalking.initialize(
		username='clientcr',
		api_key=self._get_api_key())
		sms = africastalking.SMS
		return sms
	def before_save(self):
		self.set_custom_name()
		self.make_check_digit()
		self.generate_hash()
		self.check_duplicate_ids()
		self.to_fhir()
		self.set_banner_image()
		# pass
		# if not self.nrb_image:
		# 	self.nrb_image = self.fetch_nrb_photo()
	def get_iprs_search_method(self,identification_type="National ID"):
		return frappe.get_value("Identification Type", identification_type, ["iprs_soap_method","iprs_soap_query_field"], as_dict=1)
	@frappe.whitelist()
	def iprs_search(self):
		from iprs import IPRS
		identification_type, id = self.get("identification_type"), self.get("identification_number")
		soap_method = self.get_iprs_search_method(identification_type)["iprs_soap_method"]
		soap_query_field = self.get_iprs_search_method(identification_type)["iprs_soap_query_field"]
		if not (soap_query_field or soap_method): frappe.throw("IPRS Configurations not done on the Identification Document type")
		q_args = dict(query_type=soap_method)
		q_args[soap_query_field] = id
		# frappe.throw("{}".format(q_args))
		return IPRS(**q_args).query_iprs()
	def set_banner_image(self):
		old_doc = self.get_doc_before_save()
		# if old_doc.get("client_passport_photo") != self.get("client_passport_photo"):#Only when this changes
		self.set("banner_image", self.get("client_passport_photo"))
	def after_insert(self):
		self.update_dependants()
	def set_custom_name(self):
		old_doc = self.get_doc_before_save()
		if old_doc: return
		name_format =""
		gender_id = frappe.get_value("Gender", self.get("gender"),"custom_gender_id")
		identification_number = self.get("identification_number")
		if self.related_to:
			related_to = frappe.get_doc("Client Registry", self.related_to)
			identification_number = related_to.get("identification_number")
			current_dependants =  len(related_to.get("dependants") or []) + 1  #27613716
			if (current_dependants<10 ): current_dependants = "0{}".format(current_dependants)
			name_format = "{}-{}-{}-D".format(identification_number,gender_id, current_dependants)
		else:
			name_format = "{}-{}-P".format(identification_number,gender_id)
		self.set('name', name_format)
		# frappe.rename_doc('Client Registry', self.get("name"), '{}-{}'.format(self.get("name"),cd))
		frappe.db.commit()
	def check_duplicate_ids(self):
		pass
	def generate_hash(self):
		wt_secret = frappe.db.get_single_value("Client Registry Settings","security_hash")
		if not wt_secret: frappe.throw("Error: Critical security configuration is missing. Please contact the System Administrator")
		# if self.get("related_to"): return
		# secret = "{}".format(self.date_of_birth)
		# secret = "{}".format(frappe.db.get_single_value("Client Registry Settings","security_hash"))
		id_payload = dict(identity="{}:{}".format(self.get("identification_type").lower(), self.get("identification_number").lower()).replace(" ","_"))
		encoded_jwt = jwt.encode(id_payload, wt_secret , algorithm="HS256")
		self.id_hash = encoded_jwt[:140]
		self.full_hash = encoded_jwt
	def validate_pin(self, pin):
		if not self.get("pin_number"): return False
		return str(self.get_password("pin_number")) == str(pin)
	@frappe.whitelist()
	def generate_pin(self, pin_number=None):
		self.set("pin_number" , pin_number or ''.join(random.choices(string.digits, k=N)))
		self.save(ignore_permissions=True)
		frappe.db.commit()
	@frappe.whitelist()
	def client_pin(self):
		print(self.get_password("pin_number"))
		frappe.msgprint(self.get_password("pin_number"))
		return self.get_password("pin_number")
	@frappe.whitelist()
	def send_pin_to_phone(self):
		phone = self.get("phone")
		message =  "Dear {}. The PIN for your account is {}.".format(self.get("full_name"), self.get_password("pin_number"))
		response = self.initialize_sms_provider().send(message, [phone])
		self.add_comment('Comment', text="{}".format(response))
	def to_fhir(self, **kwargs):
		unmask = (kwargs or {}).get("unmask") or frappe.db.get_single_value("Client Registry Settings","un_mask_data_on_registration")
		doc = self
		dob =  str(doc.get("date_of_birth"))
		fhir = {
			"resourceType": "Patient",
			"id": "{}".format(doc.get("name")),
			"meta": {
				"versionId": "1",
				"creationTime": "{}".format(doc.get("creation")),
				"lastUpdated": "{}".format(doc.get("modified")),
				"source": "{}".format(frappe.utils.get_url()),
			},
			"originSystem": {
				"system": "{}".format(doc.get("agent")),
				"record_id": "{}".format(doc.get("record_id") or "")
			},
			"title": doc.get("title") or "",
			"first_name": doc.get_masked_string("first_name") if not unmask else doc.get("first_name"), 
			"middle_name": doc.get_masked_string("middle_name") or "" if not unmask else doc.get("middle_name"), 
			"last_name": doc.get_masked_string("last_name") or "" if not unmask else doc.get("last_name"),
			"gender": doc.get("gender") or "",
			"date_of_birth": doc.get_masked_date("date_of_birth") if not unmask else doc.get("date_of_birth"),
   			"place_of_birth": doc.get("place_of_birth") or "" ,
			"person_with_disability": doc.get("person_with_disability", 0),
			"citizenship": doc.get_masked_string("citizenship") or "" if not unmask else doc.get("citizenship"),
			"kra_pin": self.get_masked_string("kra_pin") or "" if not unmask else doc.get("kra_pin"),
			"preferred_primary_care_network": self.get("preferred_primary_care_network") or "",
			"employment_type": doc.get("employment_type") or "",
   			"civil_status": doc.get("civil_status") or "",
			"identification_type": doc.get("identification_type"),
			"identification_number": doc.get("identification_number"),
			"other_identifications": self._other_identifications(unmask=unmask),
			"dependants": self.next_of_kins(),
			"is_alive": doc.get("is_alive") ,
			"deceased_datetime": doc.get("deceased_datetime") or "",
			"phone": doc.get_masked_string("phone") or "" if not unmask else doc.get("phone"),
   			"biometrics_verified": doc.get("biometrics_verified") or 0,
			"biometrics_score": doc.get("aws_rekognition_match") or 0,
			"email": doc.get_masked_string("email") or "" if not unmask else doc.get("email") or "",
			"country": doc.get("country") or "",
			"county": doc.get("county") or "",
			"sub_county": doc.get("sub_county") or "",
			"ward": doc.get("ward") or "",
			"village_estate": doc.get("village_estate") or "",
			"building_house_no": doc.get("building_house_no") or "",
			"latitude": doc.get("latitude") or "",
			"longitude": doc.get("longitude") or "",
			"province_state_country": doc.get("province_state_country") or "",
			"zip_code": doc.get("zip_code") or "",
			"identification_residence": doc.get("identification_residence") or "",
			"employer_name": doc.get("employer_name","") or  "",
			"employer_pin": doc.get_masked_string("employer_pin") or "" if not unmask else doc.get("employer_pin") or "",
			"disability_category": doc.get("disability_category") or "",
			"disability_subcategory": doc.get("disability_subcategory") or "",
			"disability_cause": doc.get("disability_cause") or "",
			"in_lawful_custody": doc.get("in_lawful_custody") or "",
			"admission_remand_number": doc.get_masked_string("admission_remand_number") or "" if not unmask else doc.get("admission_remand_number") or "",
			"document_uploads": self.get_uploaded_documents() or [],
			"photo": self.fetch_nrb_photo()
			# "spouse_dependant": self.get("spouse_verified")

			# "related_to": doc.get("related_to") or "",
			# "related_to_full_name": doc.get("related_to_full_name") or "",
			# "relationship": doc.get("relationship") or "",
			# "id_hash": doc.get("full_hash")

	
		}
		# frappe.msgprint("{}".format(fhir))
		# if not fhir.get
		return fhir
	def fetch_nrb_photo(self):
		if self.nrb_image: return self.nrb_image or ""
		# ecitizen_thing = self.ecitizen_mapper()
		# payload = dict(identification_type=ecitizen_thing, identification_number=self.get("identification_number"))
		# n = NRB("pin_number", **payload)
		# p = n.query_nrb().get("data")
		# if p:
		# 	return p["photo"] or ""
		# return ""
	def ecitizen_mapper(self):
		mapping = {
			"National ID": "citizen",
			"Alien ID": "alien",
			"Refugee ID": "refugee"
		}
		return mapping[self.identification_type]
	def get_masked_string(self, fieldname, plain_str=None,num_visible=3):
		s = plain_str or self.get(fieldname) or ""
		if not s: return ""
		return self.mask_digits(s, num_visible=3)
		if len(s) <= 3:
			return s[0] + s[1] + '*' * (len(s) - 3) + s[-1]
		else:
			return s[0] + s[1] + '*' * (len(s) - 4) + s[-1]
	def mask_digits(self,number_string, num_visible=1):
		if len(number_string) <= num_visible:
			return number_string
		else:
			masked_part = '*' * (len(number_string) - num_visible)
			return masked_part + number_string[-num_visible:]
	def get_masked_date(self,fieldname):
		date_obj = self.get(fieldname) or ""
		if not date_obj: return ""
		split_date = str(date_obj).split("-")
		str_array = []
		# print(split_date)
		str_array = list(map(lambda x: self.mask_digits(str(x)),split_date))
		return "-".join(str_array)
	def update_phone(self, phone):
		self.set("phone" , phone)
		self.save(ignore_permissions=True)
		frappe.db.commit()
	def spouse_dependant(self):
		sql = "SELECT B.name as id, B.relationship as relationship, B.spouse_verified as spouse_verified, B.parent AS linked_record, A.full_name FROM `tabClient Registry` A INNER JOIN `tabDependants` B ON A.name=B.parent WHERE B.relationship='Spouse' AND B.linked_record= '{}'".format(self.get("name"))
		return frappe.db.sql(sql, as_dict=1)
	def get_uploaded_documents(self):
		return frappe.db.get_all("Client Registry Document Upload", filters=dict(client=self.get("name"),docstatus=1), fields=["name","document_type","document_number", "attachment"], order_by="creation desc")
		
	def next_of_kins(self):
		payload = self.get("dependants")
		return list(map(lambda x: dict(linked_record=x.get("linked_record"), full_name="{} {}".format(x.get("first_name"), x.get("last_name")), relationship=x.get("relationship")) ,payload))
	def _other_identifications(self, **kwargs):
		unmask = frappe.db.get_single_value("Client Registry Settings","un_mask_data_on_registration") or (kwargs or {}).get("unmask")
		payload = self.get("other_identification_docs")
		return list(map(lambda x: dict(identification_type=x.get("identification_type"), identification_number=self.get_masked_string(None, plain_str=x.get("identification_number")) if not unmask else x.get("identification_number"))  ,payload))
	def update_dependants(self):
		if not self.get("related_to"): return
		is_dependant_of_doc = frappe.get_doc("Client Registry",self.get("related_to"))
		# if (is_dependant_of_doc.get("related_to")==doc.get("name")): frappe.throw("Sorry, cyclic dependency detected.")
		client_dependants = is_dependant_of_doc.get("dependants")
		records = [x.get("linked_record") for x in client_dependants]
		if self.get("name") in records: return
		is_dependant_of_doc.append("dependants", {
			"first_name": self.get("first_name"),
			"middle_name": self.get("middle_name") or "",
			"last_name": self.get("last_name"),
			"gender": self.get("gender"),
			"relationship": self.get("relationship"),
			"identification_type": self.get("identification_type"),
			"identification_number": self.get("identification_number"),
			"linked_record": self.get("name")
		})
		is_dependant_of_doc.save()
	def make_check_digit(self):
		old_doc = self.get_doc_before_save()
		if old_doc: return
		cd = self.get_checkdigit(self.get("name"))
		self.set("check_digit", cd)
		self.set('name', '{}-{}'.format(self.get("name"),cd))
		# frappe.rename_doc('Client Registry', self.get("name"), '{}-{}'.format(self.get("name"),cd))
		frappe.db.commit()
	def get_checkdigit(self, id_without_check):

		# allowable characters within identifier
		valid_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVYWXZ_-"
	
		# remove leading or trailing whitespace, convert to uppercase
		id_without_checkdigit = id_without_check.strip().upper()
	
		# this will be a running total
		sum = 0
	
		# loop through digits from right to left
		for n, char in enumerate(reversed(id_without_checkdigit)):
	
			if not valid_chars.count(char):
				raise Exception('InvalidIDException')
	
			# our "digit" is calculated using ASCII value - 48
			digit = ord(char) - 48
	
			# weight will be the current digit's contribution to
			# the running total
			weight = None
			if (n % 2 == 0):
	
				# for alternating digits starting with the rightmost, we
				# use our formula this is the same as multiplying x 2 and
				# adding digits together for values 0 to 9.  Using the
				# following formula allows us to gracefully calculate a
				# weight for non-numeric "digits" as well (from their
				# ASCII value - 48).
				## Use_sparingly: In Python 3, '/' makes floats. '//' fixes it for Python 3.
				## For cross compatibility, simply int() the result
				##                     VVVVVVVVVVVVV
				weight = (2 * digit) - int(digit / 5) * 9
			else:
				# even-positioned digits just contribute their ascii
				# value minus 48
				weight = digit
	
			# keep a running total of weights
			## Use_sparingly: removed maths.fabs()
			## abs() is sufficient
			sum += weight
	
		# avoid sum less than 10 (if characters below "0" allowed,
		# this could happen)
		sum = abs(sum) + 10
	
		# check digit is amount needed to reach next number
		# divisible by ten. Return an integer
		return int((10 - (sum % 10)) % 10)
	# def encode_url_image(self, url):
	# 	import urllib
	# 	import base64, json
	# 	url = url
	# 	contents = urllib.urlopen(url).read()
	# 	data = base64.b64encode(contents)
	# 	return data
	@frappe.whitelist()
	def image_rekognition_match(self):
		import boto3,json
		sourceFile, targetFile = self.get("client_identifier_photo_id") , self.get("client_passport_photo")
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

		response = _REKOGNITION_CLIENT.compare_faces(SimilarityThreshold=90,
										SourceImage={"S3Object": {
		        "Bucket": bucket_name,
		        "Name": sourceFile.rpartition("/"[-1])[2]
		    }},
										TargetImage={"S3Object": {
		        "Bucket": bucket_name,
		        "Name": targetFile.rpartition("/"[-1])[2]
		    }}) 
		self.db_set("aws_rekognition_payload", json.dumps(response))
		self.handle_rekognition_response(response)
		return response
	def handle_rekognition_response(self, match_response):
		face_match = match_response.get("FaceMatches")
		similarity = 0.0
		message = "There was a photo mismatch between your selfie and photo ID upload. Please reupload clear photo ID and a selfie for biometric identification."
		if not face_match:
			self.db_set("aws_rekognition_match", similarity)
			self.db_set("biometrics_verified",0)
			return
		message = "You have been biometrically verified in the digital health identity platform."
		similarity = face_match[0]["Similarity"]
		self.db_set("aws_rekognition_match", similarity)
		self.db_set("biometrics_verified",1) 
		# self.send_alert(message=message)
		# self.send_email_alert(message=message)
		# kwargs = dict(message=message)
		# frappe.enqueue(
		# 	self.send_alert, # python function or a module path as string
		# 	queue="short", # one of short, default, long
		# 	timeout=None, # pass timeout manually
		# 	is_async=True, # if this is True, method is run in worker
		# 	now=False, # if this is True, method is run directly (not in a worker) 
		# 	job_name=None, # specify a job name
		# 	enqueue_after_commit=False, # enqueue the job after the database commit is done at the end of the request
		# 	at_front=False, # put the job at the front of the queue
		# 	# dict(message=message)
		# 	**kwargs, # kwargs are passed to the method as arguments
		# )
		frappe.db.commit()
	def send_alert(self, message=None):
		phone = self.get("phone")
		message =  "{}".format(message)
		response = self.initialize_sms_provider().send(message, [phone])
		self.add_comment('Comment', text="{}".format(response))
	def send_email_alert(self, message=None):
     
		frappe.sendmail(
			recipients=[self.get("email")],
			subject=frappe._('Biometrics Verification'),
			# template='birthday_reminder',
			args=dict(
				
				message=message,
			),
			header=_('Biometrics Confirmation')
		)
	