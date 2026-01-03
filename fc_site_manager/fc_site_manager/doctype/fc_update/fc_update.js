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

        if (frm.doc.docstatus == 1) {
            frm.add_custom_button(__('Fetch Status'), async function() {
                await frm.call("get_build_status");
            });
        }
	},
});


frappe.ui.form.on("FC Update App", {
    view_diff(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        let diff_url = `${row.repository_url}/compare/${row.current_hash}...${row.hash}`
        window.open(diff_url, '_blank');
    }
});
