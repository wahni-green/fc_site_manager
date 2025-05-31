# Copyright (c) 2025, Wahni IT Solutions Pvt Ltd and contributors
# For license information, please see license.txt

import requests
import frappe
from frappe import _
from frappe.model.document import Document


class FCSettings(Document):
	def get_req_headers(self, team):
		return {
			"Authorization": f"Token {self.get_password('api_key')}:{self.get_password('api_secret')}",
			"X-Press-Team": f"{team}"
		}

	def get_fc_teams(self):
		return frappe.db.get_all(
			"FC Team",
			filters={"enabled": 1},
		)

	@frappe.whitelist()
	def get_all_sites(self):
		teams = self.get_fc_teams()
		for team in teams:
			headers = self.get_req_headers(team.name)
			response = requests.get(
				f"{self.base_url}/api/method/press.api.site.all",
				headers=headers
			)
			data = response.json()
			for site in data.get("message"):
				if frappe.db.exists("FC Site", site.get("name")):
					continue
				
				frappe.get_doc({
					"doctype": "FC Site",
					"site_name": site.get("name"),
					"fc_team": team.name,
				}).insert(ignore_permissions=True)

		frappe.msgprint(_("All sites have been fetched successfully."))
