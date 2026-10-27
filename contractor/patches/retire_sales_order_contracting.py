"""Restore app-owned Sales Order customizations without deleting historical values."""
import json
from pathlib import Path

import frappe


def execute():
    data = json.loads(Path(__file__).with_name("retired_sales_order_fields.json").read_text())
    for field in data["fields"]:
        name = frappe.db.get_value("Custom Field", field, "name")
        if name:
            frappe.db.set_value("Custom Field", name, {"hidden": 1, "in_list_view": 0, "reqd": 0})
    for name in data["setters"]:
        if frappe.db.exists("Property Setter", name):
            frappe.delete_doc("Property Setter", name)
    for name in data["links"]:
        frappe.db.delete("DocType Link", {"name": name})
    frappe.clear_cache()
