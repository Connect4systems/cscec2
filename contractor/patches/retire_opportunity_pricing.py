"""Hide legacy tender fields without deleting historical Opportunity data."""
import frappe


def execute():
    for doctype, fields in {
        "Opportunity Item": ["is_group", "series_number", "parent_group", "group_item", "item_description"],
        "Opportunity": ["group_items", "section_break_7gqac"],
    }.items():
        for field in fields:
            name = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": field}, "name")
            if name:
                frappe.db.set_value("Custom Field", name, {"hidden": 1, "in_list_view": 0, "reqd": 0})
    # Remove only the Property Setters shipped by this app.
    for name in ["Opportunity Item-qty-columns", "Opportunity Item-item_group-hidden",
                 "Opportunity Item-rate-default", "Opportunity Item-amount-default",
                 "Opportunity Item-item_group-columns"]:
        if frappe.db.exists("Property Setter", name):
            frappe.delete_doc("Property Setter", name)
    for name in frappe.get_all("DocType Link", filters={"parent": "Opportunity", "link_doctype": "Costing Note"}, pluck="name"):
        frappe.db.delete("DocType Link", {"name": name})
    frappe.clear_cache()
