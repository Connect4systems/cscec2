"""Initialize new deduction totals without resaving or repricing existing tenders."""
import frappe


def execute():
    for doc in frappe.get_all("Tender Analysis", fields=["name", "total_amount"]):
        if not frappe.db.exists("Deduction", {"parent": doc.name,
                "parenttype": "Tender Analysis", "parentfield": "deductions"}):
            frappe.db.set_value("Tender Analysis", doc.name,
                {"total_deductions": 0, "net_payable": doc.total_amount or 0}, update_modified=False)
