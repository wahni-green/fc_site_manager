// Copyright (c) 2025, Wahni IT Solutions Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("FC Site", {
	refresh(frm) {
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
                frm.add_custom_button(
                    __("Fetch Agent Jobs"), async function () {
                        frappe.dom.freeze("Fetching agent jobs...");
                        let r;
                        try {
                            r = await frm.call("fetch_agent_jobs");
                        } finally {
                            frappe.dom.unfreeze();
                        }

                        let jobs = r.message || [];
                        if (!jobs.length) {
                            frappe.msgprint(__("No agent jobs found."));
                            return;
                        }

                        let rows = jobs.map(job => `
                            <tr>
                                <td>${frappe.utils.escape_html(job.creation)}</td>
                                <td>${frappe.utils.escape_html(job.job_type)}</td>
                                <td>${frappe.utils.escape_html(job.status)}</td>
                                <td>${frappe.utils.escape_html(job.duration)}</td>
                                <td>
                                    <button class="btn btn-xs btn-default job-details-btn" data-job="${frappe.utils.escape_html(job.name)}">
                                        ${__("Details")}
                                    </button>
                                </td>
                            </tr>
                        `).join("");

                        let dialog = new frappe.ui.Dialog({
                            title: __("Agent Jobs"),
                            size: "large",
                            fields: [
                                {
                                    fieldname: "jobs_html",
                                    fieldtype: "HTML",
                                    options: `
                                        <table class="table table-bordered">
                                            <thead>
                                                <tr>
                                                    <th>${__("Created")}</th>
                                                    <th>${__("Job Type")}</th>
                                                    <th>${__("Status")}</th>
                                                    <th>${__("Duration")}</th>
                                                    <th></th>
                                                </tr>
                                            </thead>
                                            <tbody>${rows}</tbody>
                                        </table>
                                    `
                                }
                            ]
                        });

                        dialog.$wrapper.on("click", ".job-details-btn", async function () {
                            let job_name = $(this).data("job");
                            frappe.dom.freeze("Fetching job details...");
                            try {
                                await frm.call("get_agent_job_details", { job_name });
                            } finally {
                                frappe.dom.unfreeze();
                            }
                        });

                        dialog.show();
                    }, __("Tools")
                );
            }
        }

        frm.add_custom_button(
            __("Update"),
            async function () {
                frappe.new_doc("FC Update", { "bench_id": frm.doc.bench_id, "fc_team": frm.doc.fc_team });
            }, __("Tools")
        );

        frm.add_custom_button(
            __("Upgrade Version"),
            async function () {
                frappe.new_doc("FC Version Upgrade", { "site": frm.doc.name, "fc_team": frm.doc.fc_team });
            }, __("Tools")
        );
	},
});
