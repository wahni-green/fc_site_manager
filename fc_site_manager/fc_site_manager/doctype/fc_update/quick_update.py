# Copyright (c) 2025, Wahni IT Solutions Pvt Ltd and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils.data import cint, now_datetime

from fc_site_manager.fc_site_manager.doctype.fc_update.release_info import ReleaseInfo

# Dialog choice -> hour of day (system time zone).
SLOT_HOURS = {"night": 20, "tonight": 2, "early_morning": 4}


class QuickUpdate:
	"""Starts an FC Update for the bench of an FC Site without the manual form steps."""

	def __init__(self, site):
		self.site = frappe.get_doc("FC Site", site)
		self.site.check_permission("read")
		frappe.has_permission("FC Update", "create", throw=True)
		if self.site.is_external:
			frappe.throw(_("External sites can't be updated from here."))

	def options(self):
		"""Fresh apps and sites with the default selection applied."""
		info = self._fetch()
		for app in info["apps"]:
			app["selected"] = app["update_available"]

		for site in info["sites"]:
			site["selected"] = int(site["site"] == self.site.name)
			site["allow_fc_user_to_update"] = cint(
				frappe.get_cached_value("FC Site", site["site"], "allow_fc_user_to_update")
			)

		return {
			"apps": info["apps"],
			"sites": info["sites"],
			"can_submit": self._can_submit(),
		}

	def create(self, apps, sites, when, scheduled_datetime=None):
		# Data is fetched again; the dialog could be stale.
		info = self._fetch()
		selected_apps = self._validate_apps(apps, info["apps"])
		selected_sites = self._validate_sites(sites, info["sites"])

		doc = frappe.get_doc({
			"doctype": "FC Update",
			"bench_id": self.site.bench_id,
			"fc_team": self.site.fc_team,
			"requested_by": frappe.session.user,
			"scheduled_datetime": resolve_schedule(when, scheduled_datetime),
			"apps": [{**a, "deploy": int(a["app"] in selected_apps)} for a in info["apps"]],
			"sites": [self._site_row(s, selected_sites) for s in info["sites"]],
		})
		doc.insert()
		if not self._can_submit():
			return {"name": doc.name, "submitted": 0}

		doc.submit()
		return {"name": doc.name, "submitted": 1}

	def _can_submit(self):
		return frappe.has_permission("FC Update", "submit")

	def _fetch(self):
		return ReleaseInfo(self.site.bench_id, self.site.fc_team).fetch()

	def _validate_apps(self, apps, fetched):
		updatable = {a["app"] for a in fetched if a["update_available"]}
		selected = set(apps)
		if not selected:
			frappe.throw(_("Select at least one app to update."))

		if invalid := selected - updatable:
			frappe.throw(_("No update available for: {0}").format(", ".join(sorted(invalid))))

		return selected

	def _validate_sites(self, sites, fetched):
		known = {s["site"] for s in fetched}
		selected = {s["site"]: s for s in sites if s.get("update_site")}
		if not selected:
			frappe.throw(_("Select at least one site to update."))

		if invalid := set(selected) - known:
			frappe.throw(_("Unknown sites on this bench: {0}").format(", ".join(sorted(invalid))))

		return selected

	def _site_row(self, fetched, selected):
		chosen = selected.get(fetched["site"])
		if not chosen:
			return {**fetched, "update_site": 0}

		return {
			**fetched,
			"update_site": 1,
			"skip_backups": cint(chosen.get("skip_backups")),
			"skip_failing_patches": cint(chosen.get("skip_failing_patches")),
		}


def resolve_schedule(when, scheduled_datetime=None):
	"""Map the dialog choice to a datetime. `None` means deploy now."""
	if when == "now":
		return None

	if when in SLOT_HOURS:
		return next_slot(SLOT_HOURS[when])

	if when == "custom" and scheduled_datetime:
		return scheduled_datetime

	frappe.throw(_("Choose when to update."))


def next_slot(hour):
	"""Next occurrence of `hour`:00 in the system time zone."""
	now = now_datetime()
	slot = now.replace(hour=hour, minute=0, second=0, microsecond=0)
	return slot if slot > now else slot + timedelta(days=1)
