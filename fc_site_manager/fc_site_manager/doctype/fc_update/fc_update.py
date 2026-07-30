# Copyright (c) 2025, Wahni IT Solutions Pvt Ltd and contributors
# For license information, please see license.txt

import requests

import frappe
from frappe import _
from frappe.utils.data import cint, escape_html, get_datetime, now_datetime, format_datetime
from frappe.model.document import Document


class FCUpdate(Document):
	def validate(self):
		if self.is_new():
			self.get_release_groups()

		sites_for_update = [str(d.site).split(".")[0] for d in self.sites if d.update_site]
		self.title = ", ".join(sites_for_update) if sites_for_update else self.bench_id
		self.check_allow_fc_user_to_update()
		self.validate_scheduled_datetime()

	def validate_scheduled_datetime(self):
		if not self.scheduled_datetime or self.docstatus != 0:
			return

		if get_datetime(self.scheduled_datetime) <= now_datetime():
			frappe.throw(_("Scheduled Datetime must be in the future."))

	def check_allow_fc_user_to_update(self):
		self.allow_fc_user_to_update = 1
		for site in self.sites:
			if not site.update_site:
				continue
			
			if not frappe.get_cached_value(
				"FC Site", site.site, "allow_fc_user_to_update"
			):
				self.allow_fc_user_to_update = 0
				break

	def on_submit(self):
		if self.scheduled_datetime and get_datetime(self.scheduled_datetime) > now_datetime():
			self.db_set("deployment_status", "Scheduled")
			frappe.msgprint(
				_("Deployment has been scheduled for {0}.").format(
					format_datetime(self.scheduled_datetime)
				)
			)
			return

		self.initiate_deployment()

	def on_cancel(self):
		frappe.thow("FC Update cannot be cancelled.")

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

		if not sites:
			frappe.throw("No sites selected for deployment.")

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

		data = response.json()
		if pipeline := data.get("message"):
			self.db_set("release_pipeline", pipeline)

		if data.get("exc_type"):
			frappe.log_error(
				"FC Update Deployment Failed",
				response.text,
			)
			frappe.throw("Failed to initiate deployment.")

		self.db_set("deployment_status", "Initiated")
		frappe.msgprint("Deployment initiated successfully.")

	def get_deploy_candidate(self):
		if self.deploy_candidate:
			return

		settings = frappe.get_cached_doc("FC Settings")
		headers = settings.get_req_headers(self.fc_team)

		response = requests.post(
			f"{settings.base_url}/api/method/press.api.bench.deploy_status",
			headers=headers,
			json={"name": self.bench_id}
		)
		data = response.json().get("message")
		if not data:
			frappe.throw(
				f"Deploy Candidate Build not found. {response.text}."
			)

		if data.get("is_validating"):
			frappe.msgprint("Deploy is being validated. Will start soon.")

		if dc := data.get("candidate"):
			self.db_set("deploy_candidate", dc)

	@frappe.whitelist()
	def force_start_deployment(self):
		if self.docstatus != 1 or self.deployment_status != "Scheduled":
			frappe.throw(_("Only a scheduled update can be force started."))

		from fc_site_manager.scheduler import claim_scheduled_update, deploy_scheduled_update

		if not claim_scheduled_update(self.name):
			frappe.throw(_("This update is no longer scheduled."))

		try:
			frappe.enqueue(deploy_scheduled_update, queue="long", update=self.name)
		except Exception:
			frappe.db.set_value("FC Update", self.name, "deployment_status", "Failed")
			frappe.db.commit()
			raise

		frappe.msgprint(_("Deployment has been queued to start now."))

	@frappe.whitelist()
	def get_build_status(self):
		settings = frappe.get_cached_doc("FC Settings")
		headers = settings.get_req_headers(self.fc_team)

		if not self.deploy_candidate:
			self.get_deploy_candidate()

		if not self.deploy_candidate:
			return

		response = requests.post(
			f"{settings.base_url}/api/method/press.api.client.get",
			headers=headers,
			json={"doctype": "Deploy Candidate Build", "name": self.deploy_candidate}
		)
		data = response.json().get("message")
		if not data:
			frappe.throw(
				f"Deploy Candidate Build not found. {response.text}."
			)
		
		build_status = f"Build Status: {data.get('status')}"
		build_status += "<br>Build Steps:<br>"
		for step in data.get("build_steps", []):
			build_status += f"{step.get('stage')} - {step.get('step')}: {step.get('status')}<br>"
		frappe.msgprint(build_status)

	@frappe.whitelist()
	def get_pipeline_status(self):
		if not self.release_pipeline:
			frappe.throw(_("Release Pipeline not found."))

		settings = frappe.get_cached_doc("FC Settings")
		headers = settings.get_req_headers(self.fc_team)

		try:
			response = requests.post(
				f"{settings.base_url}/api/method/press.api.client.get",
				headers=headers,
				json={"doctype": "Release Pipeline", "name": self.release_pipeline},
				timeout=30
			)
			response.raise_for_status()
			data = response.json().get("message")
		except requests.RequestException:
			frappe.throw(_("Failed to reach Frappe Cloud to fetch the Release Pipeline status."))

		if not isinstance(data, dict):
			frappe.throw(
				f"Release Pipeline not found. {response.text}."
			)

		steps = data.get("steps")
		stages = steps.get("stages", []) if isinstance(steps, dict) else []
		if not isinstance(stages, list):
			stages = []

		pipeline_status = f"Pipeline Status: {escape_html(data.get('status'))}"
		pipeline_status += "<br>Stages:<br>"
		deploy_candidate = None
		for stage in stages:
			if not isinstance(stage, dict):
				continue

			pipeline_status += f"{escape_html(stage.get('label'))}: {escape_html(stage.get('status'))}<br>"
			for build in stage.get("builds", []):
				if isinstance(build, dict) and build.get("name"):
					deploy_candidate = build.get("name")

		if deploy_candidate:
			self.db_set("deploy_candidate", deploy_candidate)

		frappe.msgprint(pipeline_status)

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
					"current_hash": app.get("current_hash"),
					"repository_url": app.get("repository_url"),
					"update_available": cint(app.get("update_available"))
				}
			)

		frappe.msgprint("Release groups fetched successfully.")

	@frappe.whitelist()
	def get_app_latest_update(self, app_name):
		settings = frappe.get_cached_doc("FC Settings")
		headers = settings.get_req_headers(self.fc_team)
		requests.post(
			f"{settings.base_url}/api/method/press.api.bench.fetch_latest_app_update",
			headers=headers,
			json={"name": self.bench_id, "app": app_name}
		)

		frappe.msgprint(f"Latest update for {app_name} fetched successfully.")
		self.get_release_groups()
