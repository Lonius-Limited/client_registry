# Copyright (c) 2024, Lonius Limited and contributors
# For license information, please see license.txt

import frappe, africastalking
from frappe import _
from frappe.model.document import Document


def _get_api_key():
	return frappe.db.get_single_value("Client Registry Settings","africastalking_sms_api")
africastalking.initialize(
username='clientcr',
api_key=_get_api_key())
sms = africastalking.SMS

class OTPRecord(Document):
	def after_insert(self):
		self.send_email()
		self.send_message()
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
	def send_email(self):
		email = self.get("email")
		if email:
		# def send_email_alert(self, message=None):
			frappe.sendmail(
				recipients=[email],
				subject=frappe._('One Time PIN'),
				# template='birthday_reminder',
				now=True,
				args=dict(
					
					message="Your One Time Pin(OTP) is {}".format(self.get("key")),
				),
				header=_('One Time PIN')
			)
			self.add_comment('Comment', text="{}".format("Email OTP has been sent."))
	# def send_sms(self):
# {
# message: {
# otp_record: "3159bea508"
# }
# }