import frappe
import json

@frappe.whitelist()
def client_lookup(payload):
	# frappe.msgprint(payload.get('client_id'))
	"""
	Everything that was posted by the validated EMR to the IOL will be passed in here.
	We need to search using the parameters provided and if none is found, create and return the CR number back to the IOL
	"""
	national_id, huduma_no, passport_no, birth_cert_no, birth_notification_no = payload.get("national_id"), payload.get("huduma_no"), payload.get("passport_no"), payload.get("birth_cert_no"), payload.get("birth_notification_no")
	facility_id, facility_client_id = payload.get("facility_id"), payload.get("facility_client_id")
	main_table_filters = {}
	child_table_filters = {}
	if national_id:
		main_table_filters['identification_number'] = national_id
	if huduma_no:
		main_table_filters['huduma_number'] = huduma_no
	if passport_no:
		main_table_filters['passport_number'] = passport_no
	if birth_cert_no:
		main_table_filters['birth_certificate_number'] = birth_cert_no
	if birth_notification_no:
		main_table_filters['birth_notification_number'] = birth_notification_no
	if facility_id and facility_client_id:
		child_table_filters['institution_id'] = facility_id
		child_table_filters['client_number'] = facility_client_id
	client_no_data = frappe.db.get_list('Client Registry', filters=main_table_filters, fields=['name'])
	client_no = None
	if client_no_data and client_no_data[0]:
		client_no = client_no_data[0].get('name')
	else:
		client_no_data = frappe.db.get_list('Client Registry Institution Numbers', filters=child_table_filters, fields=['parent'])
		if client_no_data and client_no_data[0]:
			client_no = client_no_data[0].get('parent')
	if client_no:
		_update_institution_number(client_no, payload)
		return _map_fields(client_no, payload)
	else:
		#CREATE A NEW RECORD -:
		client_no = _register_client(payload)
		return _map_fields(client_no, payload)

def _map_fields(client_no, payload):
	client_doc = frappe.get_doc('Client Registry', client_no)
	payload.update({'client_id': client_no})
	if payload.get('first_name'):
		client_doc.set('first_name', payload.get('first_name'))
	if payload.get('last_name'):
		client_doc.set('last_name', payload.get('last_name'))
	if payload.get('middle_name'):
		client_doc.set('middle_name', payload.get('middle_name'))
	if payload.get('gender'):
		client_doc.set('gender', payload.get('gender'))
	if payload.get('date_of_birth'):
		client_doc.set('date_of_birth', payload.get('date_of_birth'))
	if payload.get('phone'):
		client_doc.set('phone', payload.get('phone'))
	if payload.get('email'):
		client_doc.set('email', payload.get('email'))
	if payload.get('national_id'):
		client_doc.set('identification_number', payload.get('national_id'))
	if payload.get('huduma_no'):
		client_doc.set('huduma_number', payload.get('huduma_no'))
	if payload.get('passport_no'):
		client_doc.set('passport_number', payload.get('passport_no'))
	if payload.get('birth_cert_no'):
		client_doc.set('birth_certificate_number', payload.get('birth_cert_no'))
	if payload.get('birth_notification_no'):
		client_doc.set('birth_notification_number', payload.get('birth_notification_no'))
	client_doc.save()
	payload.update({'first_name': client_doc.get("first_name")})
	payload.update({'last_name': client_doc.get("last_name")})
	payload.update({'middle_name': client_doc.get("middle_name")})
	payload.update({'gender': client_doc.get("gender")})
	payload.update({'date_of_birth': client_doc.get("date_of_birth")})
	payload.update({'phone': client_doc.get("phone")})
	payload.update({'email': client_doc.get("email")})
	payload.update({'national_id': client_doc.get("identification_number")})
	payload.update({'huduma_no': client_doc.get("huduma_number")})
	payload.update({'passport_no': client_doc.get("passport_number")})
	payload.update({'birth_cert_no': client_doc.get("birth_certificate_number")})
	payload.update({'birth_notification_no': client_doc.get("birth_notification_number")})
	return payload

def _register_client(payload):
	new_client = frappe.get_doc({
		'doctype': 'Client Registry',
		'first_name': payload.get('first_name'),
		'last_name': payload.get('last_name'),
		'middle_name': payload.get('middle_name'),
		'gender': payload.get('gender'),
		'date_of_birth': payload.get('date_of_birth'),
		'phone': payload.get('phone'),
		'email': payload.get('email'),
		'identification_number': payload.get('national_id'),
		'huduma_number': payload.get('huduma_no'),
		'passport_number': payload.get('passport_no'),
		'birth_certificate_number': payload.get('birth_cert_no'),
		'birth_notification_number': payload.get('birth_notification_no')
	})
	new_client.insert()
	_update_institution_number(new_client.get('name'), payload)
	return new_client.get('name')

def _update_institution_number(client_no, payload):
	facility_id, facility_client_id = payload.get("facility_id"), payload.get("facility_client_id")
	if facility_id and facility_client_id:
		if not frappe.db.exists({"doctype": "Client Registry Institution Numbers", "parent": client_no, "institution_id": facility_id, "client_number": facility_client_id}):
			frappe.get_doc({
				'doctype': 'Client Registry Institution Numbers',
				'parent': client_no,
				'institution_id': facility_id,
				'client_number': facility_client_id,
				'parentfield': 'institution_numbers',
				'parenttype': 'Client Registry'
			}).db_insert()