"""Restore Quotation's standard items while preserving legacy grouping values."""
import frappe


def execute():
    for fieldname in ("is_group", "series_number", "parent_group", "group_item"):
        name = frappe.db.get_value("Custom Field", {"dt": "Quotation Item", "fieldname": fieldname}, "name")
        if name:
            frappe.db.set_value("Custom Field", name, {"hidden": 1, "in_list_view": 0, "reqd": 0})
    for name in ("Quotation Item-qty-columns", "Quotation Item-item_code-columns", "Quotation Item-item_group-columns"):
        if frappe.db.exists("Property Setter", name):
            frappe.delete_doc("Property Setter", name)
    for doctype in ("Quotation", "Quotation Item"):
        frappe.clear_cache(doctype=doctype)
