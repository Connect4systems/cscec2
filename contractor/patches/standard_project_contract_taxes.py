"""Move legacy contract tax rows to the standard ERPNext child table."""
import frappe


def execute():
    from frappe.model.naming import set_new_name

    for fieldname in ("contracting_settings", "default_business_guarantee_insurance_account",
                      "advance_payment_discount_account"):
        name = frappe.db.get_value("Custom Field", {"dt": "Company", "fieldname": fieldname}, "name")
        if name:
            frappe.db.set_value("Custom Field", name, {"hidden": 1, "in_list_view": 0, "reqd": 0})
    # Copy rather than reprice history, including submitted contracts.
    for parent in frappe.get_all("Project Contract", fields=["name", "docstatus", "net_total", "conversion_rate"]):
        if frappe.db.exists("Sales Taxes and Charges", {"parent": parent.name, "parenttype": "Project Contract", "parentfield": "taxes"}):
            continue
        cumulative = parent.net_total or 0
        for old in frappe.get_all("Project Contract Tax", filters={"parent": parent.name,
                "parenttype": "Project Contract", "parentfield": "taxes"}, fields=["*"], order_by="idx asc"):
            cumulative += old.tax_amount or 0
            row = frappe.get_doc(dict(doctype="Sales Taxes and Charges", parent=parent.name,
                parenttype="Project Contract", parentfield="taxes", docstatus=parent.docstatus,
                idx=old.idx, charge_type=old.charge_type, account_head=old.account_head,
                description=old.description or old.account_head, rate=old.rate,
                tax_amount=old.tax_amount, base_tax_amount=old.base_tax_amount,
                tax_amount_after_discount_amount=old.tax_amount,
                base_tax_amount_after_discount_amount=old.base_tax_amount, total=cumulative,
                base_total=cumulative * (parent.conversion_rate or 1)))
            set_new_name(row)
            row.db_insert()
    frappe.clear_cache(doctype="Company")
