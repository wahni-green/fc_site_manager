# Copyright (c) 2026, Wahni IT Solutions Pvt Ltd and Contributors
# See license.txt

from unittest.mock import patch

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
