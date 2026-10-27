"""Read-only checks for a project's clauses, certificates, invoices and journals."""
import frappe
from frappe.utils import flt


@frappe.whitelist()
def check(project):
    doc = frappe.get_doc("Project", project)
    doc.check_permission("read")
    from contractor.project_progress import CERTIFICATES, executed_quantities
    from contractor.clearance_accounting import WORK_ITEM
    issues = []
    totals = {kind: executed_quantities(project, kind) for kind in CERTIFICATES}
    for row in doc.get("project_clauses") or []:
        if row.is_group:
            continue
        for kind in CERTIFICATES:
            if totals[kind].get(row.name, 0) > flt(row.qty)+0.000001:
                issues.append(f"{kind}: executed quantity exceeds clause {row.series_number}")
    invoices = set()
    certificates = []
    for kind in CERTIFICATES:
        for name in frappe.get_all(kind, filters={"project": project, "legacy_record": 0, "docstatus": 1}, pluck="name"):
            certificate = frappe.get_doc(kind, name)
            certificate.check_permission("read")
            certificates.append(name)
            if not certificate.invoice:
                issues.append(f"{name}: no invoice")
                continue
            key = (certificate.invoice_doctype, certificate.invoice)
            if key in invoices:
                issues.append(f"{name}: invoice is shared with another certificate")
            invoices.add(key)
            invoice = frappe.get_doc(*key)
            invoice.check_permission("read")
            if invoice.docstatus != 1 or len(invoice.items) != 1 or invoice.items[0].item_name != WORK_ITEM:
                issues.append(f"{name}: invoice must be submitted with one work item")
            if abs(flt(invoice.grand_total)-flt(certificate.grand_total)) > 0.01:
                issues.append(f"{name}: invoice/certificate total mismatch")
            if certificate.total_deductions and not certificate.deduction_entry:
                issues.append(f"{name}: missing deduction journal")
            if certificate.deduction_entry:
                entry = frappe.get_doc("Journal Entry", certificate.deduction_entry)
                entry.check_permission("read")
                difference = sum(flt(row.debit)-flt(row.credit) for row in entry.accounts)
                if entry.docstatus != 1 or abs(difference) > 0.001:
                    issues.append(f"{name}: deduction journal is not submitted/balanced")
    return {"project": project, "submitted_certificates": certificates, "issues": issues, "ok": not issues}
