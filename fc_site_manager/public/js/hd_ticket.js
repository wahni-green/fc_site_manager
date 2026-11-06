const FC_SITE_API = "fc_site_manager.fc_site_manager.doctype.fc_site.fc_site";
const FC_SITE_GROUP = __("FC Site");

frappe.ui.form.on("HD Ticket", {
	async refresh(frm) {
		if (frm.is_new() || !frm.doc.customer) return;

		const roles = ["FC User", "FC Admin", "Agent"];
		if (!roles.some((role) => frappe.user.has_role(role))) return;

		const { message: sites } = await frappe.call({
			method: `${FC_SITE_API}.get_sites_for_ticket`,
			args: { ticket: frm.doc.name },
		});

		if (!sites.length) {
			frm.add_custom_button(__("Link Site"), () => show_link_dialog(frm), FC_SITE_GROUP);
			return;
		}

		for (const site of sites) {
			frm.add_custom_button(
				__("Login to {0}", [site]),
				() => login_to_site(frm, site),
				FC_SITE_GROUP
			);
		}
	},
});

async function show_link_dialog(frm) {
	const { message: sites } = await frappe.call({ method: `${FC_SITE_API}.get_unlinked_sites` });
	const dialog = new frappe.ui.Dialog({
		title: __("Link Site to {0}", [frm.doc.customer]),
		fields: [
			{
				label: __("FC Site"),
				fieldname: "site",
				fieldtype: "Autocomplete",
				options: sites,
				reqd: 1,
			},
		],
		primary_action_label: __("Link"),
		async primary_action({ site }) {
			await frappe.call({
				method: `${FC_SITE_API}.link_site_to_ticket_customer`,
				args: { ticket: frm.doc.name, site },
			});
			dialog.hide();
			frm.reload_doc();
		},
	});
	dialog.show();
}

async function login_to_site(frm, site) {
	frappe.dom.freeze(__("Fetching credentials..."));
	let response;
	try {
		response = await frappe.call({
			method: `${FC_SITE_API}.login_to_site_from_ticket`,
			args: { ticket: frm.doc.name, site },
		});
	} finally {
		frappe.dom.unfreeze();
	}
	open_url_post(`https://${site}/app`, { sid: response.message }, true);
}
