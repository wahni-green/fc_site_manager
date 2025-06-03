# Copyright (c) 2025, Wahni IT Solutions Pvt Ltd and contributors
# For license information, please see license.txt

import json
import requests
import frappe
from frappe import _
from frappe.model.document import Document


class FCSite(Document):
	def get_fc_settings(self):
		return frappe.get_cached_doc("FC Settings")

	def login_as_admin(self):
		if self.login_restricted:
			frappe.throw(_("Login is restricted for this site."))
		
		settings = self.get_fc_settings()
		data = {"name": self.name}

		response = requests.post(
			f"{settings.base_url}/api/method/press.api.site.login",
			headers=settings.get_req_headers(self.fc_team),
			json=data
		)

		sid = response.json().get("message").get("sid")
		if not sid:
			frappe.throw(_("Login failed."))
		
		return sid

	@frappe.whitelist()
	def disable_instance_users(self):
		frappe.only_for("FC Admin")
		sid = self.login_as_admin()

		for row in self.users:
			requests.put(
				f"https://{self.site_name}/api/resource/User/{row.user}",
				cookies={"sid": sid},
				json={"enabled": 0}
			).raise_for_status()

		frappe.msgprint(_("All users have been disabled for this site."))

	@frappe.whitelist()
	def fetch_instance_users(self):
		frappe.only_for("FC Admin")
		settings = self.get_fc_settings()
		sid = self.login_as_admin()

		filters = settings.get_user_filters()
		filters.append(
			["name", "!=", "Administrator"]
		)
		params = {
			"fields": json.dumps(["name"]),
			"filters": json.dumps(filters)
		}
		users = requests.get(
			f"https://{self.site_name}/api/resource/User",
			cookies={"sid": sid},
			json=params
		).json()

		self.set("users", [])
		for user in users.get("data", []):
			self.append("users", {"user": user.get("name")})
		self.save()
		self.add_comment(
			"Workflow",
			f"{frappe.session.user} fetched users from {self.site_name}."
		)

	@frappe.whitelist()
	def login_to_site(self):
		user = frappe.session.user
		sid = self.login_as_admin()

		if user == "Administrator":
			self.add_comment(
				"Workflow",
				f"{frappe.session.user} logged on to {self.site_name}."
			)
			return sid

		user_doc = requests.get(
			f"https://{self.site_name}/api/resource/User/{user}",
			cookies={"sid": sid}
		).json()

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
			else:
				self.append("users", {"user": user})
				self.flags.ignore_permissions = True
				self.save()

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
		self.add_comment(
			"Workflow",
			f"{frappe.session.user} logged on to {self.site_name}."
		)

		return user_login_response.cookies.get_dict().get("sid")

	@frappe.whitelist()
	def impersonate_as_user(self, impersonate_as, reason):
		if not self.allow_impersonation:
			frappe.throw(_("Impersonation is not allowed for this site."))

		if impersonate_as == "Administrator":
			frappe.throw(_("You cannot impersonate as the Administrator."))

		if not frappe.db.exists("User", impersonate_as):
			frappe.throw(_("User {0} does not exist.").format(impersonate_as))

		if impersonate_as == frappe.session.user:
			frappe.throw(_("You are already logged in as {0}.").format(impersonate_as))

		sid = self.login_as_admin()
		user_doc = requests.get(
			f"https://{self.site_name}/api/resource/User/{impersonate_as}",
			cookies={"sid": sid}
		).json()

		if not user_doc.get("data"):
			user_creation = requests.post(
				f"https://{self.site_name}/api/resource/User",
				cookies={"sid": sid},
				json=self.generate_user_doc(impersonate_as)
			)
			try:
				user_creation.raise_for_status()
			except Exception:
				frappe.throw(user_creation.text)
			else:
				self.append("users", {"user": impersonate_as})
				self.flags.ignore_permissions = True
				self.save()

		user_login_response = requests.post(
			f"https://{self.site_name}/api/method/frappe.core.doctype.user.user.impersonate",
			cookies={"sid": sid},
			json={"user": impersonate_as, "reason": reason}
		)
		user_login_response.raise_for_status()
		self.add_comment(
			"Workflow",
			f"{frappe.session.user} impersonated as {impersonate_as} and logged on to {self.site_name}."
		)
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
