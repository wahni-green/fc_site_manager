// Copyright (c) 2026, Wahni IT Solutions Pvt Ltd and contributors
// For license information, please see license.txt

function set_destination_group_options(frm, options) {
	frm.set_df_property("destination_group", "options", options);
	frm.refresh_field("destination_group");

	if (options.length === 1) {
		frm.set_value("destination_group", options[0].value);
	}
}

frappe.ui.form.on("FC Version Upgrade", {
	refresh(frm) {
		if (frm.doc.has_existing_benches && frm.doc.destination_group) {
			let options = frm.get_field("destination_group").df.options || [];
			if (typeof options === "string") {
				options = options.split("\n");
			}
			let has_value = options.some((o) => (o.value !== undefined ? o.value : o) === frm.doc.destination_group);
			if (!has_value) {
				set_destination_group_options(frm, [
					{ label: frm.doc.destination_group, value: frm.doc.destination_group }
				]);
			}
		}

		if (frm.doc.docstatus == 0 && !frm.doc.__islocal) {
			frm.add_custom_button(__("Check Compatibility"), async function() {
				frappe.dom.freeze();
				let r;
				try {
					r = await frm.call("check_compatibility");
				} finally {
					frappe.dom.unfreeze();
				}

				if (frm.doc.has_existing_benches) {
					set_destination_group_options(frm, r.message || []);
				}
				frm.dirty();
				frm.refresh();
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
