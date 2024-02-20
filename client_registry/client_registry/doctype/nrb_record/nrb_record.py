# Copyright (c) 2024, Lonius Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class NRBRecord(Document):
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
   			"marital_status": doc.get("marital_status"),
			"identification_type": doc.get("identification_type"),
			"identification_number": doc.get("identification_number"),
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
