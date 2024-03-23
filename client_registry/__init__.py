from __future__ import unicode_literals
import frappe

__version__ = '0.0.1'
# Some Comment
def execute():
    genders = ["Male","Female","Prefer not to say","Non-Conforming","Other","Transgender"]
    identity_types =["National ID","Passport","Birth Certificate","Alien ID","KRA PIN"]
    for g in genders:
        if not frappe.db.get_value("Gender",dict(gender=g)):
            args = dict(gender=g, doctype="Gender")
            frappe.get_doc(args).insert()
    for i in identity_types:
        if not frappe.db.get_value("Identification Type",i):
            argsv = dict(id_type=i,doctype="Identification Type")
            frappe.get_doc(argsv).insert()
