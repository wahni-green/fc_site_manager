# Copyright (c) 2025, Wahni IT Solutions Pvt Ltd and contributors
# For license information, please see license.txt

import json
import requests
import frappe
from frappe import _
from frappe.model.document import Document


class FCSettings(Document):
	def validate(self):
		self.validate_filter_json()

	def validate_filter_json(self):
		if not self.user_filter:
			self.user_filter = "[]"
			return

		try:
			filters = json.loads(self.user_filter)
			if not isinstance(filters, list):
				frappe.throw(_("User Filter must be a valid JSON array."))
			for filter_item in filters:
				if not isinstance(filter_item, list):
					frappe.throw(_("Each filter item in User Filter must be a list."))
				if len(filter_item) != 3:
					frappe.throw(_("Each filter item in User Filter must contain exactly three elements: [field, operator, value]."))
		except json.JSONDecodeError:
			frappe.throw(_("Invalid JSON format in User Filter."))

	def get_req_headers(self, team):
		return {
			"Authorization": f"Token {self.get_password('api_key')}:{self.get_password('api_secret')}",
			"X-Press-Team": frappe.get_cached_value("FC Team", team, "team_id"),
		}

	def get_fc_teams(self):
		return frappe.db.get_all(
			"FC Team",
			filters={"enabled": 1},
			fields=["name", "team_id"]
		)

	def get_user_filters(self):
		return json.loads(self.user_filter) if self.user_filter else []

	@frappe.whitelist()
	def get_all_teams(self):
		headers = self.get_req_headers(self.fc_team_id)
		response = requests.post(
			f"{self.base_url}/api/method/press.api.client.get",
			headers=headers,
			json={"doctype": "Team", "name": self.fc_team_id}
		)
		data = response.json().get("message")
		for team in data.get("valid_teams"):
			if frappe.db.exists("FC Team", team.get("user")):
				continue
			
			frappe.get_doc({
				"doctype": "FC Team",
				"username": team.get("user"),
				"team_id": team.get("name"),
			}).insert(ignore_permissions=True)

		frappe.msgprint(_("All teams have been fetched successfully."))

	@frappe.whitelist()
	def get_all_sites(self):
		teams = self.get_fc_teams()
		for team in teams:
			headers = self.get_req_headers(team.team_id)
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
