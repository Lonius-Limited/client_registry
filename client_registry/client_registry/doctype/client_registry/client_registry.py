# Copyright (c) 2022, Lonius Limited and contributors
# For license information, please see license.txt

import frappe, jwt
from frappe.model.document import Document

class ClientRegistry(Document):
	# def autoname(self):
	# 	pass
	def before_save(self):
		self.set_custom_name()
		self.make_check_digit()
		self.generate_hash()
		self.check_duplicate_ids()
		self.to_fhir()
		# pass
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
		if self.get("related_to"): return
		secret = "{}".format(self.date_of_birth)
		id_payload = dict(identity="{}:{}".format(self.get("identification_type").lower(), self.get("identification_number").lower()).replace(" ","_"))
		encoded_jwt = jwt.encode(id_payload, secret , algorithm="HS256")
		self.id_hash = encoded_jwt[:140]
		self.full_hash = encoded_jwt
	def to_fhir(self):
		doc = self
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
				"system": "{}".format(doc.get("registry_system")),
				"facility_code": "{}".format(doc.get("facility_code"))
			},
			"first_name": doc.get("first_name"),
			"middle_name": doc.get("middle_name") or "",
			"last_name": doc.get("last_name") or "",
			"gender": doc.get("gender"),
			"date_of_birth": doc.get("date_of_birth"),
			"nationality": doc.get("nationality"),
			"kra_pin": self.get("kra_pin") or "",
			"preferred_primary_care_network": self.get("preferred_primary_care_network") or "",
   			"marital_status": doc.get("marital_status"),
			"identification_type": doc.get("identification_type"),
			"identification_number": doc.get("identification_number"),
			"other_identifications": self._other_identifications(),
			"dependants": self.next_of_kins(),
			"is_alive": doc.get("is_alive") ,
			"deceased_datetime": doc.get("deceased_datetime") or "",
			"phone": doc.get("phone") or "",
   			"biometrics_verified": doc.get("biometrics_verified") or 0,
			"email": doc.get("email") or "",
			"nationality": doc.get("") or "",
			"country": doc.get("country") or "",
			"county": doc.get("country") or "",
			"sub_county": doc.get("sub_county") or "",
			"ward": doc.get("ward") or "",
			"village": doc.get("village") or "",
			# "related_to": doc.get("related_to") or "",
			# "related_to_full_name": doc.get("related_to_full_name") or "",
			# "relationship": doc.get("relationship") or "",
			"id_hash": doc.get("full_hash")

	
		}
		# frappe.msgprint("{}".format(fhir))
		return fhir
	def next_of_kins(self):
	 
		payload = self.get("dependants")
		return list(map(lambda x: dict(linked_record=x.get("linked_record"), full_name="{} {}".format(x.get("first_name"), x.get("last_name")), relationship=x.get("relationship")) ,payload))
		# dependants =[]
		# if not payload : return dependants
		# for d in payload:
		# 	dependants.append(d.as_dict())
		# return dependants
	def _other_identifications(self):
		payload = self.get("other_identification_docs")
		# other_ids = []
		# if not payload: return other_ids
		# for id in payload:
		# 	other_ids.append(id.as_dict())
		# return other_ids # 
		return list(map(lambda x: dict(identification_type=x.get("identification_type"), identification_number=x.get("identification_number")) ,payload))
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

