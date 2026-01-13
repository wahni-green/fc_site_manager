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

        frm.add_custom_button(
            __("Add Permission"),
            async function() {
                let dialog = new frappe.ui.Dialog({
                    title: __("Add Permission"),
                    fields: [
                        {
                            label: __("FC Perm Docname"),
                            fieldname: "perm",
                            fieldtype: "Data",
                            reqd: 1,
                        },
                        {
                            label: __("Resource"),
                            fieldname: "resource",
                            fieldtype: "Select",
                            options: ["Site", "Release Group", "Server"],
                            default: "Site",
                            reqd: 1,
                        }
                    ],
                    primary_action_label: __("Add"),
                    primary_action: async function () {
                        let values = dialog.get_values();
                        frappe.dom.freeze();
                        await frm.call("add_resource_to_perm_groups", {
                            resource: values.resource,
                            perm: values.perm,
                        });
                        frappe.dom.unfreeze();
                        dialog.hide();
                    },
                });
                dialog.show();
            }
        )
	},
});
