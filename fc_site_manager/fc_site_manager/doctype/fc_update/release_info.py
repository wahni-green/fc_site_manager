# Copyright (c) 2025, Wahni IT Solutions Pvt Ltd and contributors
# For license information, please see license.txt

import requests

import frappe
from frappe import _
from frappe.utils.data import cint


class ReleaseInfo:
	"""Deploy information of a Frappe Cloud bench (Release Group)."""

	def __init__(self, bench_id, fc_team):
		self.bench_id = bench_id
		self.fc_team = fc_team

	def fetch(self):
		"""Return `{"apps": [...], "sites": [...]}`. Throws if the bench can't be updated."""
		data = self._get_release_group()
		deploy_info = self._validated_deploy_info(data)
		return {
			"apps": [self._app_row(app) for app in deploy_info.get("apps") or []],
			"sites": [self._site_row(site) for site in deploy_info.get("sites") or []],
		}

	def _get_release_group(self):
		settings = frappe.get_cached_doc("FC Settings")
		response = requests.post(
			f"{settings.base_url}/api/method/press.api.client.get",
			headers=settings.get_req_headers(self.fc_team),
			json={"doctype": "Release Group", "name": self.bench_id},
		)
		data = response.json().get("message")
		if not data:
			frappe.throw(_("Release Group not found. {0}.").format(response.text))

		return data

	def _validated_deploy_info(self, data):
		if data.get("status") != "Active":
			frappe.throw(_("The Release Group is not active."))

		deploy_info = data.get("deploy_information")
		if not deploy_info:
			frappe.throw(_("No deployable updates found."))

		if not deploy_info.get("update_available"):
			frappe.throw(_("No updates available."))

		if deploy_info.get("deploy_in_progress"):
			frappe.throw(_("Another deploy is already in progress."))

		return deploy_info

	def _site_row(self, site):
		return {
			"site": site.get("name"),
			"bench": site.get("bench"),
			"server": site.get("server"),
			"skip_backups": cint(site.get("skip_backups")),
			"skip_failing_patches": cint(site.get("skip_failing_patches")),
		}

	def _app_row(self, app):
		release = next(
			(d for d in app.get("releases", []) if d.get("name") == app.get("next_release")),
			{},
		)
		return {
			"app": app.get("app"),
			"release": app.get("next_release"),
			"source": release.get("source"),
			"hash": release.get("hash"),
			"current_hash": app.get("current_hash"),
			"repository_url": app.get("repository_url"),
			"update_available": cint(app.get("update_available")),
		}
