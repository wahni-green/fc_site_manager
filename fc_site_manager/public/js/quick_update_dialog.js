// Copyright (c) 2025, Wahni IT Solutions Pvt Ltd and contributors
// For license information, please see license.txt

frappe.provide("fc_site_manager");

const API = "fc_site_manager.fc_site_manager.doctype.fc_update.fc_update";

fc_site_manager.QuickUpdateDialog = class QuickUpdateDialog {
	constructor(site) {
		this.site = site;
	}

	async open() {
		frappe.dom.freeze(__("Fetching updates..."));
		try {
			const r = await frappe.call({ method: `${API}.get_update_options`, args: { site: this.site } });
			this.apps = r.message.apps;
			this.sites = r.message.sites;
			this.night_slot = r.message.night_slot;
		} finally {
			frappe.dom.unfreeze();
		}

		this.make_dialog();
		this.render();
		this.dialog.show();
	}

	make_dialog() {
		this.dialog = new frappe.ui.Dialog({
			title: __("Update {0}", [this.site]),
			size: "large",
			fields: [
				{ fieldtype: "HTML", fieldname: "apps_html" },
				{ fieldtype: "HTML", fieldname: "sites_html" },
				{
					fieldtype: "Select",
					fieldname: "when",
					label: __("When"),
					options: [
						{ value: "now", label: __("Now") },
						{ value: "tonight", label: __("Tonight at 2:00 AM") },
						{ value: "custom", label: __("Custom time") },
					],
					default: "now",
					onchange: () => this.render_warnings(),
				},
				{
					fieldtype: "Datetime",
					fieldname: "scheduled_datetime",
					label: __("Scheduled Time"),
					depends_on: "eval:doc.when=='custom'",
					mandatory_depends_on: "eval:doc.when=='custom'",
					onchange: () => this.render_warnings(),
				},
				{ fieldtype: "HTML", fieldname: "warnings_html" },
			],
			primary_action_label: __("Update"),
			primary_action: () => this.submit(),
		});
	}

	// ---- state ----

	get selected_apps() {
		return this.apps.filter(a => a.selected);
	}

	get selected_sites() {
		return this.sites.filter(s => s.selected);
	}

	get updatable_apps() {
		return this.apps.filter(a => a.update_available);
	}

	// ---- rendering ----

	render() {
		this.render_apps();
		this.render_sites();
		this.render_warnings();
	}

	render_apps() {
		const rows = this.apps.map((a, i) => `
			<tr class="${a.update_available ? "" : "text-muted"}">
				<td><input type="checkbox" data-app="${i}" ${a.selected ? "checked" : ""} ${a.update_available ? "" : "disabled"}></td>
				<td>${frappe.utils.escape_html(a.app)}</td>
				<td><code>${this.short(a.current_hash)} → ${this.short(a.hash)}</code></td>
				<td>${this.diff_link(a)}</td>
			</tr>`).join("");

		this.dialog.fields_dict.apps_html.$wrapper.html(`
			<h6>${__("Apps")}</h6>
			<table class="table table-sm">
				<thead><tr>
					<th style="width:30px"><input type="checkbox" class="select-all-apps" title="${__("Select all updatable apps")}"></th>
					<th>${__("App")}</th><th>${__("Change")}</th><th></th>
				</tr></thead>
				<tbody>${rows}</tbody>
			</table>`);

		this.bind_select_all(".select-all-apps", this.updatable_apps, this.selected_apps.length);
		this.dialog.$wrapper.find("[data-app]").on("change", e => {
			this.apps[e.target.dataset.app].selected = e.target.checked ? 1 : 0;
			this.render();
		});
	}

	render_sites() {
		const rows = this.sites.map((s, i) => `
			<tr>
				<td><input type="checkbox" data-site="${i}" ${s.selected ? "checked" : ""}></td>
				<td>${frappe.utils.escape_html(s.site)}</td>
				<td><input type="checkbox" data-skip-backups="${i}" ${s.skip_backups ? "checked" : ""}></td>
				<td><input type="checkbox" data-skip-patches="${i}" ${s.skip_failing_patches ? "checked" : ""}></td>
			</tr>`).join("");

		this.dialog.fields_dict.sites_html.$wrapper.html(`
			<h6>${__("Sites")}</h6>
			<table class="table table-sm">
				<thead><tr>
					<th style="width:30px"><input type="checkbox" class="select-all-sites" title="${__("Select all sites")}"></th>
					<th>${__("Site")}</th><th>${__("Skip Backups")}</th><th>${__("Skip Failing Patches")}</th>
				</tr></thead>
				<tbody>${rows}</tbody>
			</table>`);

		this.bind_select_all(".select-all-sites", this.sites, this.selected_sites.length);
		const $w = this.dialog.$wrapper;
		$w.find("[data-site]").on("change", e => {
			this.sites[e.target.dataset.site].selected = e.target.checked ? 1 : 0;
			this.render();
		});
		$w.find("[data-skip-backups]").on("change", e => {
			this.sites[e.target.dataset.skipBackups].skip_backups = e.target.checked ? 1 : 0;
		});
		$w.find("[data-skip-patches]").on("change", e => {
			this.sites[e.target.dataset.skipPatches].skip_failing_patches = e.target.checked ? 1 : 0;
		});
	}

	// Tri-state header checkbox: all / some / none.
	bind_select_all(selector, rows, selected_count) {
		const $box = this.dialog.$wrapper.find(selector);
		$box.prop("checked", rows.length > 0 && selected_count === rows.length);
		$box.prop("indeterminate", selected_count > 0 && selected_count < rows.length);
		$box.on("change", e => {
			rows.forEach(r => (r.selected = e.target.checked ? 1 : 0));
			this.render();
		});
	}

	render_warnings() {
		const warnings = this.get_warnings();
		this.dialog.fields_dict.warnings_html.$wrapper.html(
			warnings.map(w => `<div class="alert alert-warning py-2 mb-2">${w}</div>`).join("")
		);

		const label = this.selected_apps.length && this.selected_sites.length
			? __("Update {0} app(s) on {1} site(s)", [this.selected_apps.length, this.selected_sites.length])
			: __("Update");
		this.dialog.set_primary_action(label, () => this.submit());
		this.dialog.get_primary_btn().prop("disabled", !this.is_valid());
	}

	get_warnings() {
		const warnings = [];
		if (!this.selected_apps.length) warnings.push(__("Select at least one app."));
		if (!this.selected_sites.length) warnings.push(__("Select at least one site."));

		this.selected_apps.filter(a => a.hash === a.current_hash).forEach(a =>
			warnings.push(__("{0} is already at the target version.", [frappe.utils.escape_html(a.app)]))
		);
		this.selected_sites.filter(s => !s.allow_fc_user_to_update).forEach(s =>
			warnings.push(__("{0} does not allow FC users to update.", [frappe.utils.escape_html(s.site)]))
		);

		if (this.dialog.get_value("when") === "custom") {
			const at = this.dialog.get_value("scheduled_datetime");
			if (at && moment(at).isBefore(moment())) warnings.push(__("Scheduled time must be in the future."));
		}
		return warnings;
	}

	is_valid() {
		const custom = this.dialog.get_value("when") === "custom";
		const at = this.dialog.get_value("scheduled_datetime");
		if (custom && (!at || moment(at).isBefore(moment()))) return false;
		return this.selected_apps.length > 0 && this.selected_sites.length > 0;
	}

	// ---- submit ----

	submit() {
		if (!this.is_valid()) return;
		if (this.selected_sites.length > 1) {
			frappe.confirm(
				__("This updates {0} sites. Continue?", [this.selected_sites.length]),
				() => this.create()
			);
			return;
		}
		this.create();
	}

	async create() {
		const values = this.dialog.get_values();
		frappe.dom.freeze(__("Submitting update..."));
		try {
			const r = await frappe.call({
				method: `${API}.create_update`,
				args: {
					site: this.site,
					apps: JSON.stringify(this.selected_apps.map(a => a.app)),
					sites: JSON.stringify(this.sites.map(s => ({
						site: s.site,
						update_site: s.selected,
						skip_backups: s.skip_backups,
						skip_failing_patches: s.skip_failing_patches,
					}))),
					when: values.when,
					scheduled_datetime: values.scheduled_datetime,
				},
			});
			this.dialog.hide();
			frappe.set_route("Form", "FC Update", r.message);
		} finally {
			frappe.dom.unfreeze();
		}
	}

	// ---- helpers ----

	short(hash) {
		return hash ? hash.slice(0, 7) : "-";
	}

	diff_link(app) {
		if (!app.repository_url || !app.current_hash || !app.hash) return "";
		const url = `${app.repository_url}/compare/${app.current_hash}...${app.hash}`;
		return `<a href="${frappe.utils.escape_html(url)}" target="_blank" rel="noopener">${__("View diff")}</a>`;
	}
};
