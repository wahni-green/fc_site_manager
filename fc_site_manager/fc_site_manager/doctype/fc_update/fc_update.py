# Copyright (c) 2025, Wahni IT Solutions Pvt Ltd and contributors
# For license information, please see license.txt

import requests

import frappe
from frappe.utils.data import cint
from frappe.model.document import Document


class FCUpdate(Document):
	def validate(self):
		if self.is_new():
			self.get_release_groups()

	def on_submit(self):
		self.initiate_deployment()

	def initiate_deployment(self):
		settings = frappe.get_cached_doc("FC Settings")
		headers = settings.get_req_headers(self.fc_team)
		apps = []
		for app in self.apps:
			if not app.deploy:
				continue

			apps.append({
				"app": app.app,
				"release": app.release,
				"source": app.source,
				"hash": app.hash,
			})

		if not apps:
			frappe.throw("No apps selected for deployment.")

		sites = []
		for site in self.sites:
			if not site.update_site:
				continue

			sites.append({
				"name": site.site,
				"bench": site.bench,
				"server": site.server,
				"skip_backups": site.skip_backups,
				"skip_failing_patches": site.skip_failing_patches,
			})

		payload = {
			"name": self.bench_id,
			"apps": apps,
			"sites": sites,
			"run_will_fail_check": True
		}

		response = requests.post(
			f"{settings.base_url}/api/method/press.api.bench.deploy_and_update",
			headers=headers,
			json=payload
		)

		data = response.json().get("message")
		if not data:
			frappe.log_error(
				"FC Update Deployment Failed",
				response.text,
			)
			frappe.throw("Failed to initiate deployment.")

		frappe.msgprint("Deployment initiated successfully.")

	@frappe.whitelist()
	def get_release_groups(self):
		settings = frappe.get_cached_doc("FC Settings")
		headers = settings.get_req_headers(self.fc_team)
		response = requests.post(
			f"{settings.base_url}/api/method/press.api.client.get",
			headers=headers,
			json={"doctype": "Release Group", "name": self.bench_id}
		)
		data = response.json().get("message")

		if not data:
			frappe.throw(
				f"Release Group not found. {response.text}."
			)
			return

		if data.get("status") != "Active":
			frappe.throw("The Release Group is not active.")
			return

		if not data.get("deploy_information"):
			frappe.throw("No deployable updates found.")
			return

		deploy_info = data["deploy_information"]
		if not deploy_info.get("update_available"):
			frappe.throw("No updates available.")
			return

		if deploy_info.get("deploy_in_progress"):
			frappe.throw("Another deploy is already in progress.")
			return

		self.set("sites", [])
		for site in deploy_info.get("sites"):
			self.append(
				"sites",
				{
					"site": site.get("name"),
					"bench": site.get("bench"),
					"server": site.get("server"),
					"skip_backups": cint(site.get("skip_backups")),
					"skip_failing_patches": cint(site.get("skip_failing_patches")),
				}
			)

		self.set("apps", [])
		for app in deploy_info.get("apps"):
			release = [
				d for d in app.get("releases", [])
				if d.get("name") == app.get("next_release")
			]
			release = release[0] if release else {}

			self.append(
				"apps",
				{
					"app": app.get("app"),
					"release": app.get("next_release"),
					"source": release.get("source"),
					"hash": release.get("hash"),
					"update_available": cint(app.get("update_available"))
				}
			)

		frappe.msgprint("Release groups fetched successfully.")
