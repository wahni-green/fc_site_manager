# Copyright (c) 2025, Wahni IT Solutions Pvt Ltd and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import create_batch, now_datetime


def process_scheduled_updates():
    updates = frappe.get_all(
        "FC Update",
        filters={
            "docstatus": 1,
            "deployment_status": "Scheduled",
            "scheduled_datetime": ["<=", now_datetime()],
        },
        pluck="name",
    )

    for name in updates:
        current_status = frappe.db.get_value(
            "FC Update", name, "deployment_status", for_update=True
        )
        if current_status != "Scheduled":
            frappe.db.commit()
            continue

        frappe.db.set_value("FC Update", name, "deployment_status", "Queued")
        frappe.db.commit()

        try:
            frappe.enqueue(deploy_scheduled_update, queue="long", update=name)
        except Exception as e:
            frappe.db.set_value("FC Update", name, "deployment_status", "Failed")
            frappe.db.commit()
            frappe.log_error(
                message=str(e),
                title=f"Error enqueueing scheduled deployment for {name}"
            )


def deploy_scheduled_update(update):
    doc = frappe.get_doc("FC Update", update)
    try:
        doc.initiate_deployment()
    except Exception as e:
        frappe.db.set_value("FC Update", update, "deployment_status", "Failed")
        frappe.log_error(
            message=str(e),
            title=f"Error initiating scheduled deployment for {update}"
        )


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
