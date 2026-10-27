import frappe


def execute():
    from contractor.tender_pricing import sync_tender_boq_links
    for name in frappe.get_all("Tender Analysis", pluck="name"):
        sync_tender_boq_links(name)
