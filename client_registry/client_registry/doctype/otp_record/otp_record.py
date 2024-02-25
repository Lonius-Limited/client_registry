# Copyright (c) 2024, Lonius Limited and contributors
# For license information, please see license.txt

import frappe, africastalking

from frappe.model.document import Document

africastalking.initialize(
username='clientcr',
api_key=frappe.db.get_single_value("Client Registry Settings","africastalking_sms_api"))
sms = africastalking.SMS

class OTPRecord(Document):
	def after_insert(self):
		return
		phone = self.get("phone")
		message =  "Your One Time Pin(OTP) is {}".format(self.get("key"))
		response = sms.send(message, [phone])
		self.add_comment('Comment', text="{}".format(response))
	def send_message(self):
		phone = self.get("phone")
		message =  "Your One Time Pin(OTP) is {}".format(self.get("key"))
		response = sms.send(message, [phone])
		self.add_comment('Comment', text="{}".format(response))
		
	# def send_sms(self):
# {
# message: {
# otp_record: "3159bea508"
# }
# }