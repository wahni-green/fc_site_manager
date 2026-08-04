# Copyright (c) 2026, Wahni IT Solutions Pvt Ltd and Contributors
# See license.txt

from types import SimpleNamespace
from unittest.mock import patch

import requests

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestFCVersionUpgrade(IntegrationTestCase):
	"""
	Integration tests for FCVersionUpgrade.
	Use this class for testing interactions between multiple components.
	"""

	def new_upgrade(self, scheduled_datetime=None):
		doc = frappe.new_doc("FC Version Upgrade")
		doc.scheduled_datetime = scheduled_datetime
		return doc

	def test_validate_scheduled_datetime_rejects_past(self):
		doc = self.new_upgrade(add_to_date(now_datetime(), minutes=-10))
		self.assertRaises(frappe.ValidationError, doc.validate_scheduled_datetime)

	def test_validate_scheduled_datetime_allows_future(self):
		doc = self.new_upgrade(add_to_date(now_datetime(), minutes=10))
		doc.validate_scheduled_datetime()

	def test_validate_scheduled_datetime_allows_empty(self):
		doc = self.new_upgrade(None)
		doc.validate_scheduled_datetime()

	def test_validate_scheduled_datetime_skips_on_cancel(self):
		doc = self.new_upgrade(add_to_date(now_datetime(), minutes=-10))
		doc._action = "cancel"
		doc.validate_scheduled_datetime()

	def test_get_scheduled_time_ist_none_when_empty(self):
		doc = self.new_upgrade(None)
		self.assertIsNone(doc.get_scheduled_time_ist())

	def test_get_scheduled_time_ist_converts_to_kolkata(self):
		doc = self.new_upgrade("2026-01-15 10:00:00")
		with patch(
			"fc_site_manager.fc_site_manager.doctype.fc_version_upgrade.fc_version_upgrade.get_system_timezone",
			return_value="America/New_York",
		):
			result = doc.get_scheduled_time_ist()
		self.assertEqual(result, "2026-01-15T20:30")

	def fake_settings(self):
		return SimpleNamespace(base_url="https://example.com", get_req_headers=lambda team: {})

	def test_initiate_upgrade_does_not_commit_before_raising(self):
		doc = self.new_upgrade(None)
		doc.release_group_title = "Test Upgrade"
		doc.append("apps", {
			"app": "test_app",
			"branch": "main",
			"repository_url": "https://github.com/example/test_app",
		})

		with patch.object(doc, "get_fc_settings", return_value=self.fake_settings()), patch(
			"fc_site_manager.fc_site_manager.doctype.fc_version_upgrade.fc_version_upgrade.requests.post",
			side_effect=requests.RequestException("network down"),
		), patch("frappe.db.commit") as mock_commit:
			self.assertRaises(frappe.ValidationError, doc.initiate_upgrade)
			mock_commit.assert_not_called()

	def test_upgrade_via_existing_bench_does_not_commit_before_raising(self):
		doc = self.new_upgrade(None)
		doc.has_existing_benches = 1
		doc.destination_group = "bench-1"

		with patch.object(doc, "get_fc_settings", return_value=self.fake_settings()), patch(
			"fc_site_manager.fc_site_manager.doctype.fc_version_upgrade.fc_version_upgrade.requests.post",
			side_effect=requests.RequestException("network down"),
		), patch("frappe.db.commit") as mock_commit:
			self.assertRaises(frappe.ValidationError, doc.upgrade_via_existing_bench)
			mock_commit.assert_not_called()
