# Copyright (c) 2025, Wahni IT Solutions Pvt Ltd and Contributors
# See license.txt

from datetime import datetime
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase

from fc_site_manager.fc_site_manager.doctype.fc_update.fc_update import get_press_error
from fc_site_manager.fc_site_manager.doctype.fc_update.quick_update import (
	QuickUpdate,
	next_slot,
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


class TestNextSlot(UnitTestCase):
	def test_before_two_am_uses_today(self):
		with patch("fc_site_manager.fc_site_manager.doctype.fc_update.quick_update.now_datetime",
				return_value=datetime(2026, 11, 12, 1, 0)):
			self.assertEqual(next_slot(2), datetime(2026, 11, 12, 2, 0))

	def test_after_two_am_uses_tomorrow(self):
		with patch("fc_site_manager.fc_site_manager.doctype.fc_update.quick_update.now_datetime",
				return_value=datetime(2026, 11, 12, 14, 30)):
			self.assertEqual(next_slot(2), datetime(2026, 11, 13, 2, 0))

	def test_resolve_named_slots(self):
		with patch("fc_site_manager.fc_site_manager.doctype.fc_update.quick_update.now_datetime",
				return_value=datetime(2026, 11, 12, 10, 0)):
			self.assertEqual(resolve_schedule("night"), datetime(2026, 11, 12, 20, 0))
			self.assertEqual(resolve_schedule("early_morning"), datetime(2026, 11, 13, 4, 0))

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


class TestQuickUpdateCreate(UnitTestCase):
	def create(self, submitted):
		obj = quick_update()
		obj.site.update(is_external=0)
		doc = MagicMock()
		doc.name = "FCU-1"
		with patch.object(obj, "_fetch", return_value=FETCHED), \
			patch.object(obj, "_submit", return_value=submitted), \
			patch.object(frappe, "get_doc", return_value=doc):
			result = obj.create(["frappe"], [{"site": "a.example.com", "update_site": 1}], "now")
		return result, doc

	def test_reports_submitted(self):
		result, doc = self.create(submitted=True)
		doc.insert.assert_called_once()
		self.assertEqual(result, {"name": "FCU-1", "submitted": 1})

	def test_reports_draft(self):
		result, _ = self.create(submitted=False)
		self.assertEqual(result, {"name": "FCU-1", "submitted": 0})


class TestQuickUpdateSubmit(UnitTestCase):
	def submit(self, roles, has_permission=True):
		doc = MagicMock()
		with patch.object(frappe, "get_roles", return_value=roles), \
			patch.object(frappe, "has_permission", return_value=has_permission):
			return quick_update()._submit(doc), doc

	def test_fc_admin_submits(self):
		submitted, doc = self.submit(["FC User", "FC Admin"])
		self.assertTrue(submitted)
		doc.submit.assert_called_once()

	def test_fc_user_gets_draft(self):
		submitted, doc = self.submit(["FC User"])
		self.assertFalse(submitted)
		doc.submit.assert_not_called()

	def test_admin_without_submit_permission_gets_draft(self):
		submitted, doc = self.submit(["FC Admin"], has_permission=False)
		self.assertFalse(submitted)
		doc.submit.assert_not_called()


class TestPressError(UnitTestCase):
	def test_prefers_server_messages(self):
		data = {"_server_messages": '["{\\"message\\": \\"Bad <b>app</b>\\"}"]', "exception": "x"}
		self.assertEqual(get_press_error(data), "Bad &lt;b&gt;app&lt;/b&gt;")

	def test_falls_back_to_exception(self):
		self.assertEqual(get_press_error({"exception": "Boom", "exc_type": "ValidationError"}), "Boom")
