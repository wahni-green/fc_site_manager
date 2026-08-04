// Copyright (c) 2026, Wahni IT Solutions Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("FC Version Upgrade", {
	refresh(frm) {
		if (frm.doc.docstatus == 0 && !frm.doc.__islocal) {
			frm.add_custom_button(__("Check Compatibility"), async function() {
				await frm.call("check_compatibility");
				frm.dirty();
			}, __("Actions"));
		}

		if (frm.doc.docstatus == 1 && frm.doc.release_group) {
			frm.add_custom_button(__("Fetch Status"), async function() {
				await frm.call("get_upgrade_status");
			}, __("Actions"));
		}
	},
});

frappe.ui.form.on("FC Version Upgrade App", {
	fetch_branches(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frappe.dom.freeze();
		frm.call("get_app_branches", { app: row.app })
			.then((r) => {
				frappe.dom.unfreeze();
				let branches = r.message || [];
				let dialog = new frappe.ui.Dialog({
					title: __("Choose Branch for {0}", [row.app]),
					fields: [
						{
							fieldname: "branch",
							fieldtype: "Select",
							label: __("Branch"),
							options: branches,
							default: row.branch,
							reqd: 1
						}
					],
					primary_action_label: __("Set Branch"),
					primary_action(values) {
						frappe.model.set_value(cdt, cdn, "branch", values.branch);
						dialog.hide();
					}
				});
				dialog.show();
			})
			.catch(() => frappe.dom.unfreeze());
	}
});
