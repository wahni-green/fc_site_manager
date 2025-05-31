# Copyright (c) 2025, Wahni IT Solutions Pvt Ltd and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import create_batch


def schedule_site_actions():
    if not frappe.get_cached_doc("FC Settings").fetch_and_disable_users:
        return

    sites = frappe.get_all("FC Site")
    for batch in create_batch(sites, 15):
        frappe.enqueue(
			fetch_and_disable_users,
			queue="long",
            sites=batch,
		)


def fetch_and_disable_users(sites):
    for site in sites:
        try:
            site_doc = frappe.get_doc("FC Site", site.name)
            site_doc.fetch_instance_users()
            site_doc.disable_instance_users()
        except Exception as e:
            frappe.log_error(
                message=str(e),
                title=f"Error processing site: {site.name}"
            )
            continue
