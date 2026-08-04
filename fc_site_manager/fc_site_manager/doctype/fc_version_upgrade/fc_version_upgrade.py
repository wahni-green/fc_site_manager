# Copyright (c) 2026, Wahni IT Solutions Pvt Ltd and contributors
# For license information, please see license.txt

import json

import requests

import frappe
from frappe import _
from frappe.utils import escape_html
from frappe.utils.data import get_datetime, now_datetime
from frappe.model.document import Document


class FCVersionUpgrade(Document):
	def validate(self):
		if self.is_new():
			self.fetch_site_details()

		self.validate_scheduled_datetime()

	def validate_scheduled_datetime(self):
		if not self.scheduled_datetime or self.docstatus != 0:
			return

		if get_datetime(self.scheduled_datetime) <= now_datetime():
			frappe.throw(_("Scheduled Datetime must be in the future."))

	def on_submit(self):
		self.initiate_upgrade()

	def on_cancel(self):
		frappe.throw("FC Version Upgrade cannot be cancelled.")

	def get_fc_settings(self):
		return frappe.get_cached_doc("FC Settings")

	def fetch_site_details(self):
		site = frappe.get_cached_doc("FC Site", self.site)
		self.fc_team = site.fc_team
		self.current_version = site.version
		if not self.release_group_title:
			self.release_group_title = f"{site.site_name.split('.')[0]} Upgrade"

	def raise_for_api_error(self, response):
		try:
			data = response.json()
		except ValueError:
			frappe.throw(_("Unexpected response from Frappe Cloud. {0}").format(response.text))

		if not data.get("exc_type"):
			return data

		message = data.get("exc_type")
		if server_messages := data.get("_server_messages"):
			try:
				for raw in json.loads(server_messages):
					message = json.loads(raw).get("message", message)
			except ValueError:
				pass

		frappe.log_error("FC Version Upgrade Failed", response.text)
		frappe.throw(message)

	@frappe.whitelist()
	def check_compatibility(self):
		if self.docstatus != 0:
			frappe.throw(_("Compatibility can only be checked on a draft document."))

		settings = self.get_fc_settings()
		headers = settings.get_req_headers(self.fc_team)
		payload = {"name": self.site, "version": self.current_version}

		try:
			response = requests.post(
				f"{settings.base_url}/api/method/press.api.version_upgrade.check_existing_upgrade_bench",
				headers=headers,
				json=payload,
				timeout=30
			)
		except requests.RequestException:
			frappe.throw(_("Failed to reach Frappe Cloud to check for an existing upgrade bench."))

		existing = self.raise_for_api_error(response).get("message") or {}
		if existing.get("benches"):
			frappe.msgprint(
				_("An upgrade bench already exists for this site: {0}").format(
					", ".join(existing.get("benches"))
				),
				indicator="orange"
			)

		try:
			response = requests.post(
				f"{settings.base_url}/api/method/press.api.version_upgrade.check_app_compatibility_for_upgrade",
				headers=headers,
				json=payload,
				timeout=30
			)
		except requests.RequestException:
			frappe.throw(_("Failed to reach Frappe Cloud to check app compatibility."))

		data = self.raise_for_api_error(response).get("message")
		if not data:
			frappe.throw(_("App compatibility check returned no data. {0}").format(response.text))

		incompatible = {d.get("app") for d in data.get("incompatible", [])}

		self.set("apps", [])
		for app in data.get("site_custom_apps", []):
			self.append("apps", {
				"app": app.get("app"),
				"title": app.get("title"),
				"source": app.get("source"),
				"repository": app.get("repository"),
				"repository_url": app.get("repository_url"),
				"repository_owner": app.get("repository_owner"),
				"current_branch": app.get("branch"),
				"branch": app.get("branch"),
				"incompatible": 1 if app.get("app") in incompatible else 0,
			})

		self.can_upgrade = 1 if data.get("can_upgrade") else 0
		if not self.can_upgrade:
			frappe.msgprint(
				_("This site cannot be upgraded yet. Choose a compatible branch for the incompatible apps below."),
				indicator="orange"
			)
		else:
			frappe.msgprint(_("App compatibility checked successfully."))

	@frappe.whitelist()
	def get_app_branches(self, app):
		row = next((d for d in self.apps if d.app == app), None)
		if not row:
			frappe.throw(_("App {0} not found.").format(app))

		settings = self.get_fc_settings()
		headers = settings.get_req_headers(self.fc_team)

		try:
			response = requests.post(
				f"{settings.base_url}/api/method/press.api.github.branches",
				headers=headers,
				json={
					"owner": row.repository_owner,
					"name": row.repository,
					"app_source": row.source,
				},
				timeout=30
			)
		except requests.RequestException:
			frappe.throw(_("Failed to reach Frappe Cloud to fetch branches for {0}.").format(app))

		branches = self.raise_for_api_error(response).get("message")
		if branches is None:
			frappe.throw(_("Failed to fetch branches for {0}. {1}.").format(app, response.text))

		return [b.get("name") for b in branches]

	def initiate_upgrade(self):
		if not self.apps:
			frappe.throw(_("Please check app compatibility before submitting."))

		settings = self.get_fc_settings()
		headers = settings.get_req_headers(self.fc_team)

		custom_app_sources = [
			{
				"app": row.app,
				"branch": row.branch,
				"repository_url": row.repository_url,
			}
			for row in self.apps
		]

		is_scheduled = bool(self.scheduled_datetime) and get_datetime(self.scheduled_datetime) > now_datetime()
		scheduled_time = get_datetime(self.scheduled_datetime) if is_scheduled else now_datetime()

		try:
			response = requests.post(
				f"{settings.base_url}/api/method/press.api.version_upgrade.create_private_bench_for_site_upgrade",
				headers=headers,
				json={
					"name": self.site,
					"version": self.current_version,
					"release_group_title": self.release_group_title,
					"custom_app_sources": custom_app_sources,
					"scheduled_time": scheduled_time.strftime("%Y-%m-%dT%H:%M"),
					"skip_failing_patches": bool(self.skip_failing_patches),
					"skip_backups": bool(self.skip_backups),
				},
				timeout=60
			)
		except requests.RequestException:
			frappe.throw(_("Failed to reach Frappe Cloud to initiate the version upgrade."))

		data = self.raise_for_api_error(response)
		release_group = data.get("message")
		if not release_group:
			frappe.throw(_("Failed to initiate version upgrade. {0}").format(response.text))

		self.db_set("release_group", release_group)
		self.db_set("upgrade_status", "Scheduled" if is_scheduled else "Initiated")
		frappe.msgprint(_("Version upgrade initiated successfully."))

	@frappe.whitelist()
	def get_upgrade_status(self):
		if not self.release_group:
			frappe.throw(_("Release Group not found."))

		settings = self.get_fc_settings()
		headers = settings.get_req_headers(self.fc_team)

		try:
			response = requests.post(
				f"{settings.base_url}/api/method/press.api.client.get_list",
				headers=headers,
				json={
					"doctype": "Bench",
					"fields": ["name", "status"],
					"filters": {"group": self.release_group},
					"order_by": "creation desc",
					"limit_page_length": 5,
				},
				timeout=30
			)
		except requests.RequestException:
			frappe.throw(_("Failed to reach Frappe Cloud to fetch the Bench status."))

		benches = self.raise_for_api_error(response).get("message")
		if not isinstance(benches, list):
			benches = []

		status = f"Release Group: {escape_html(self.release_group)}<br>"
		if benches:
			status += "Benches:<br>"
			for bench in benches:
				status += f"{escape_html(bench.get('name'))}: {escape_html(bench.get('status'))}<br>"
		else:
			status += "No bench created yet. It may still be queued."

		frappe.msgprint(status)
