# Copyright (c) 2026, Wahni IT Solutions Pvt Ltd and Contributors
# See license.txt

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
		doc = self.new_upgrade(add_to_date(now_datetime(), minutes=30))
		result = doc.get_scheduled_time_ist()
		self.assertIsNotNone(result)
		self.assertRegex(result, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")
