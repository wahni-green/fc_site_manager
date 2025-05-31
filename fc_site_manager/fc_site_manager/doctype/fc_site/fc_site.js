// Copyright (c) 2025, Wahni IT Solutions Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("FC Site", {
	refresh(frm) {
        if (!frm.doc.login_restricted) {
            frm.add_custom_button(
                __("Login"), async function () {
                    frappe.dom.freeze("Fetching credentials...");
                    let credentials = await frm.call("login_to_site");
                    frappe.dom.unfreeze();
                    open_url_post(
                        `https://${frm.doc.site_name}/app`,
                        {
                            sid: credentials.message,
                        },
                        true
                    );
                }
            );
            if (frappe.user.has_role("System Manager")) {
                frm.add_custom_button(
                    __("Fetch Users"), async function () {
                        frappe.dom.freeze("Fetching users...");
                        await frm.call("fetch_instance_users");
                        frappe.dom.unfreeze();
                    }, __("Tools")
                );
                frm.add_custom_button(
                    __("Disable Users"), async function () {
                        frappe.dom.freeze("Disabling users...");
                        await frm.call("disable_instance_users");
                        frappe.dom.unfreeze();
                    }, __("Tools")
                );
            }
        }
	},
});
