# Copyright (c) 2024, Lonius Limited and contributors
# For license information, please see license.txt

import frappe, africastalking

from frappe.model.document import Document

africastalking.initialize(
username='clientcr',
api_key='421a7e42e07e312613ef30f1316b62615cb9ea5eb4aadcd47f955686d568a53a')
sms = africastalking.SMS

class OTPRecord(Document):
	def after_insert(self):
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