# Copyright (c) 2025, Wahni IT Solutions Pvt Ltd and Contributors
# See license.txt

from datetime import datetime
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from fc_site_manager.fc_site_manager.doctype.fc_update.fc_update import get_press_error
from fc_site_manager.fc_site_manager.doctype.fc_update.quick_update import (
	QuickUpdate,
	night_slot,
	resolve_schedule,
)

FETCHED = {
	"apps": [
		{"app": "frappe", "update_available": 1, "hash": "b", "current_hash": "a"},
		{"app": "erpnext", "update_available": 0, "hash": "c", "current_hash": "c"},
	],
	"sites": [{"site": "a.example.com"}, {"site": "b.example.com"}],
}


def quick_update():
	"""QuickUpdate without touching FC Site or permissions."""
	obj = QuickUpdate.__new__(QuickUpdate)
	obj.site = frappe._dict(name="a.example.com", bench_id="bench-1", fc_team="team")
	return obj


class TestNightSlot(UnitTestCase):
	def test_before_two_am_uses_today(self):
		with patch("fc_site_manager.fc_site_manager.doctype.fc_update.quick_update.now_datetime",
				return_value=datetime(2026, 11, 12, 1, 0)):
			self.assertEqual(night_slot(), datetime(2026, 11, 12, 2, 0))

	def test_after_two_am_uses_tomorrow(self):
		with patch("fc_site_manager.fc_site_manager.doctype.fc_update.quick_update.now_datetime",
				return_value=datetime(2026, 11, 12, 14, 30)):
			self.assertEqual(night_slot(), datetime(2026, 11, 13, 2, 0))

	def test_resolve_schedule(self):
		self.assertIsNone(resolve_schedule("now"))
		self.assertEqual(resolve_schedule("custom", "2030-01-01 10:00:00"), "2030-01-01 10:00:00")
		with self.assertRaises(frappe.ValidationError):
			resolve_schedule("custom")


class TestQuickUpdateValidation(UnitTestCase):
	def test_rejects_app_without_update(self):
		with self.assertRaises(frappe.ValidationError):
			quick_update()._validate_apps(["erpnext"], FETCHED["apps"])

	def test_rejects_empty_selection(self):
		with self.assertRaises(frappe.ValidationError):
			quick_update()._validate_apps([], FETCHED["apps"])
		with self.assertRaises(frappe.ValidationError):
			quick_update()._validate_sites([{"site": "a.example.com", "update_site": 0}], FETCHED["sites"])

	def test_rejects_unknown_site(self):
		with self.assertRaises(frappe.ValidationError):
			quick_update()._validate_sites([{"site": "x.example.com", "update_site": 1}], FETCHED["sites"])

	def test_site_row_keeps_user_flags_only_for_selected(self):
		selected = quick_update()._validate_sites(
			[{"site": "a.example.com", "update_site": 1, "skip_backups": 1}], FETCHED["sites"]
		)
		row = quick_update()._site_row(FETCHED["sites"][0], selected)
		self.assertEqual((row["update_site"], row["skip_backups"]), (1, 1))
		self.assertEqual(quick_update()._site_row(FETCHED["sites"][1], selected)["update_site"], 0)


class TestPressError(UnitTestCase):
	def test_prefers_server_messages(self):
		data = {"_server_messages": '["{\\"message\\": \\"Bad <b>app</b>\\"}"]', "exception": "x"}
		self.assertEqual(get_press_error(data), "Bad &lt;b&gt;app&lt;/b&gt;")

	def test_falls_back_to_exception(self):
		self.assertEqual(get_press_error({"exception": "Boom", "exc_type": "ValidationError"}), "Boom")
