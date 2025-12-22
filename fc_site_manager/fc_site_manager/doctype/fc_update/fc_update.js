// Copyright (c) 2025, Wahni IT Solutions Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("FC Update", {
	refresh(frm) {
        if (frm.doc.docstatus == 0 && !frm.doc.__islocal) {
            frm.add_custom_button(__('Check for Updates'), async function() {
                await frm.call("get_release_groups");
                frm.dirty();
            });
        }
	},
});
