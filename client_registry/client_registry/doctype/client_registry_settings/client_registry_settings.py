# Copyright (c) 2024, Lonius Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class ClientRegistrySettings(Document):
    pass
@frappe.whitelist()
def all_client_registry_fields():
	return [x.get("fieldname") for x in frappe.db.get_all("DocField", filters=dict(parent="Client Registry" , fieldtype=["NOT IN",["Section Break","Tab Break", "Section Break","Column Break"]]),fields=["fieldname"],order_by="reqd DESC")]
