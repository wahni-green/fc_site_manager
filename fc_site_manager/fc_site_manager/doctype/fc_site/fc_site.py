# Copyright (c) 2025, Wahni IT Solutions Pvt Ltd and contributors
# For license information, please see license.txt

import requests
import frappe
from frappe import _
from frappe.model.document import Document


class FCSite(Document):
	def get_fc_settings(self):
		return frappe.get_cached_doc("FC Settings")

	@frappe.whitelist()
	def login_to_site(self):
		if self.login_restricted:
			frappe.throw(_("Login is restricted for this site."))

		user = frappe.session.user
		settings = self.get_fc_settings()
		data = {
			"name": self.name,
		}

		response = requests.post(
			f"{settings.base_url}/api/method/press.api.site.login",
			headers=settings.get_req_headers(self.fc_team),
			json=data
		)

		sid = response.json().get("message").get("sid")
		if not sid:
			frappe.throw(_("Login failed."))

		user_doc = requests.get(
			f"https://{self.site_name}/api/resource/User/{user}",
			cookies={"sid": sid}
		).json()

		# if user_doc.get("exc_type") == "DoesNotExistError":
		if not user_doc.get("data"):
			user_creation = requests.post(
				f"https://{self.site_name}/api/resource/User",
				cookies={"sid": sid},
				json=self.generate_user_doc(user)
			)
			try:
				user_creation.raise_for_status()
			except Exception:
				frappe.throw(user_creation.text)

		random_password = frappe.generate_hash(length=12)
		requests.put(
			f"https://{self.site_name}/api/resource/User/{user}",
			cookies={"sid": sid},
			json={"enabled": 1, "new_password": random_password}
		).raise_for_status()

		user_login_response = requests.post(
			f"https://{self.site_name}/api/method/login",
			json={"usr": user, "pwd": random_password}
		)
		user_login_response.raise_for_status()
		return user_login_response.cookies.get_dict().get("sid")


	def generate_user_doc(self, username=None):
		username = username or frappe.session.user
		user = frappe.db.get_value(
			"User",
			username,
			["name", "email", "first_name", "last_name"],
			as_dict=True
		)
		user["send_welcome_email"] = 0
		user["roles"] = [
			{
                "idx": 1,
                "role": "System Manager",
            },
		]
		return user
