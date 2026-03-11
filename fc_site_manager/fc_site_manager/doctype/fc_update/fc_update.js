// Copyright (c) 2025, Wahni IT Solutions Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("FC Update", {
	refresh(frm) {
        if (frm.doc.docstatus == 0 && !frm.doc.__islocal) {
            frm.add_custom_button(__('Check for Updates'), async function() {
                await frm.call("get_release_groups");
                frm.dirty();
            }, __("Actions"));

            frm.add_custom_button(__("Fetch Latest Update for App"), async function() {
                let dialog = new frappe.ui.Dialog({
                    title: __("Fetch Latest Update for App"),
                    fields: [
                        {
                            fieldname: "app_name",
                            fieldtype: "Select",
                            label: __("App"),
                            options: frm.doc.apps.map(d => d.app),
                            reqd: 1
                        }
                    ],
                    primary_action_label: __("Fetch Update"),
                    async primary_action(values) {
                        frappe.dom.freeze();
                        try {
                            await frm.call("get_app_latest_update", { app_name: values.app_name });
                        } finally {
                            frappe.dom.unfreeze();
                        }
                        dialog.hide();
                    }
                });
                dialog.show();
            }, __("Actions"));
        }

        if (frm.doc.docstatus == 1) {
            frm.add_custom_button(__('Fetch Status'), async function() {
                await frm.call("get_build_status");
            }, __("Actions"));
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
