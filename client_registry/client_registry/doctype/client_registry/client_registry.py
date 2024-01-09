# Copyright (c) 2022, Lonius Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class ClientRegistry(Document):
	def before_save(self):
		self.make_check_digit()
		self.to_fhir()
		# pass
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
   			"marital_status": doc.get("marital_status"),
			"identification_type": doc.get("identification_type"),
			"identification_number": doc.get("identification_number"),
			"next_of_kins": self.next_of_kins(),
			"is_alive": doc.get("is_alive") ,
			"deceased_datetime": doc.get("deceased_datetime") or "",
			"phone": doc.get("phone") or "",
			"email": doc.get("email") or "",
			"country": doc.get("country") or "",
			"county": doc.get("country") or "",
			"sub_county": doc.get("sub_county") or "",
			"ward": doc.get("ward") or "",
			"village": doc.get("village") or "",
			"related_to": doc.get("related_to") or "",
			"related_to_full_name": doc.get("related_to_full_name") or "",
			"relationship": doc.get("relationship") or "",

	
		}
		# frappe.msgprint("{}".format(fhir))
		return fhir
	def next_of_kins(self):
		payload = self.get("dependants")
		dependants =[]
		if not payload : return dependants
		for d in payload:
			dependants.append(d.as_dict())
		return dependants
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

