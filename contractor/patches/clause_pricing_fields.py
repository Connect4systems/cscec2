"""Refresh clause-pricing metadata without changing historical documents."""
import frappe


def execute():
    for slug in ('costing_note', 'costing_note_items', 'template_boq'):
        frappe.reload_doc('contractor_app', 'doctype', slug, force=True)
    frappe.clear_cache()
