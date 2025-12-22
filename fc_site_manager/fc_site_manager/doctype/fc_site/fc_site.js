// Copyright (c) 2025, Wahni IT Solutions Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("FC Site", {
	refresh(frm) {
        frm.add_custom_button(
            __("Update"),
            async function () {
                frappe.new_doc("FC Update", {"bench_id": frm.doc.bench_id});
            }, __("Actions")
        );

        if (!frm.doc.login_restricted) {
            frm.add_custom_button(
                __("Self"), async function () {
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
                }, __("Login")
            );

            if (frm.doc.allow_impersonation) {
                frm.add_custom_button(
                    __("Impersonate"), async function () {
                        let dialog = new frappe.ui.Dialog({
                            title: __("Impersonate User"),
                            fields: [
                                {
                                    label: __("User"),
                                    fieldname: "user",
                                    fieldtype: "Link",
                                    options: "User",
                                    reqd: 1,
                                    get_query() {
                                        return {
                                            filters: {
                                                enabled: 1,
                                                user_type: "System User",
                                                name: ["not in", [frappe.session.user, "Administrator"]],
                                            },
                                        };
                                    },
                                },
                                {
                                    "label": __("Reason"),
                                    "fieldname": "reason",
                                    "fieldtype": "Small Text",
                                    "reqd": 1,
                                }
                            ],
                            primary_action_label: __("Impersonate"),
                            primary_action(values) {
                                dialog.hide();
                                frappe.dom.freeze("Fetching credentials...");
                                frm.call("impersonate_as_user", {
                                    impersonate_as: values.user,
                                    reason: values.reason,
                                }).then((r) => {
                                    frappe.dom.unfreeze();
                                    open_url_post(
                                        `https://${frm.doc.site_name}/app`,
                                        {
                                            sid: r.message,
                                        },
                                        true
                                    );
                                });
                            },
                        });
                        dialog.show();
                    }, __("Login")
                );
            }

            if (frappe.user.has_role("FC Admin")) {
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
