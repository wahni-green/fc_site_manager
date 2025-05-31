// Copyright (c) 2025, Wahni IT Solutions Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("FC Settings", {
	refresh(frm) {
        frm.add_custom_button(
            __("Sites"), async function() {
                frappe.dom.freeze();
                await frm.call("get_all_sites");
                frappe.dom.unfreeze();
            }, __("Sync")
        );

        frm.add_custom_button(
            __("Teams"), async function() {
                frappe.dom.freeze();
                await frm.call("get_all_teams");
                frappe.dom.unfreeze();
            }, __("Sync")
        );
	},
});
