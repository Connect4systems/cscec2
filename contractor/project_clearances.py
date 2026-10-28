"""Period certificates, source identities, quantity limits, and lifecycle."""
import frappe
from frappe.utils import flt, today

from contractor.document_mapping import copy_child_values
from contractor.progress_rules import certificate_quantity, quantity
from contractor.project_progress import CERTIFICATES, executed_quantities, refresh_project


def lock_project(project):
    frappe.db.sql("select name from `tabProject` where name=%s for update", project)


def sources(project):
    doc = frappe.get_doc("Project", project)
    doc.check_permission("read")
    if not doc.get("project_contract"):
        frappe.throw("Select a Project created from a Project Contract")
    if doc.status == "Cancelled":
        frappe.throw("Cannot certify a cancelled Project")
    contract = frappe.get_doc("Project Contract", doc.project_contract)
    contract.check_permission("read")
    if contract.docstatus != 1:
        frappe.throw("Project Contract must be submitted")
    if doc.company != contract.company or doc.customer != contract.customer:
        frappe.throw("Project company and customer must match the Project Contract")
    return doc, contract


def contract_row(project_row, contract):
    matches = [row for row in contract.clauses if row.name == project_row.get("contract_clause_row")]
    if not matches:
        matches = [row for row in contract.clauses if row.source_row == project_row.source_row
            and row.contractual_clause == project_row.contractual_clause]
    if len(matches) != 1:
        frappe.throw("The Project clause cannot be uniquely matched to its Project Contract")
    return matches[0]


@frappe.whitelist()
def create_clearance(project, doctype="Project Clearnce", supplier=None):
    if doctype not in CERTIFICATES:
        frappe.throw("Unsupported certificate type")
    project_doc, contract = sources(project)
    doc = frappe.new_doc(doctype)
    doc.check_permission("create")
    buying = doctype == "Subcontract Clearnce"
    doc.update(dict(project=project_doc.name, project_contract=contract.name,
        project_offer=contract.get("project_offer"), tender_analysis=contract.tender_analysis,
        title=project_doc.project_name, company=contract.company, currency=contract.currency,
        conversion_rate=contract.conversion_rate, posting_date=today(), transaction_date=today(),
        delivery_date=contract.delivery_date, legacy_record=0, status="Draft",
        customer=None if buying else contract.customer, supplier=supplier if buying else None,
        apply_discount_on="Net Total", disable_rounded_total=contract.get("disable_rounded_total")))
    for row in project_doc.project_clauses:
        source = contract_row(row, contract)
        doc.append("clauses", dict(project_clause_ref=row.name, is_group=row.is_group,
            contractual_clause=row.contractual_clause, clause_title=row.clause_title,
            source_row=row.source_row, series_number=row.series_number, parent_series=row.parent_series,
            qty=0, rate=0 if buying or row.is_group else source.rate, uom=row.uom,
            total_required_qty=row.qty, costing_note=row.costing_note, submitted_boq=row.submitted_boq))
    if not buying:
        doc.selling_deductions_template = contract.get("selling_deductions_template")
        for row in contract.deductions:
            doc.append("deductions", copy_child_values(row))
        doc.taxes_and_charges = contract.get("taxes_and_charges")
        for row in contract.taxes:
            values = copy_child_values(row)
            if row.charge_type == "Actual":
                values["tax_amount"] = 0  # Fixed charges must be entered for this period, not rebilled in full.
            doc.append("taxes", values)
    set_quantities(doc, project_doc)
    return doc


def set_quantities(doc, project):
    if doc.doctype == "Subcontract Clearnce" and doc.get("subcontractor_contract"):
        from contractor.subcontracting import set_contract_quantities
        return set_contract_quantities(doc, project)
    done = executed_quantities(project.name, doc.doctype, exclude=doc.name)
    party_done = executed_quantities(project.name, doc.doctype, exclude=doc.name, supplier=doc.get("supplier"))
    source_rows = {row.name: row for row in project.project_clauses}
    seen = set()
    positive = False
    for row in doc.clauses:
        source = source_rows.get(row.project_clause_ref)
        if not source or row.project_clause_ref in seen:
            frappe.throw("Each certificate row must reference a unique clause belonging to this Project")
        seen.add(row.project_clause_ref)
        for field in ("is_group", "series_number", "parent_series", "clause_title", "contractual_clause", "uom", "source_row"):
            row.set(field, source.get(field))
        if source.is_group:
            row.qty = row.rate = row.amount = 0
            continue
        previous = done.get(source.name, 0)
        try:
            current = quantity(row.qty)
            row.remaining_qty = certificate_quantity(source.qty, previous, current)
        except ValueError as exc:
            frappe.throw(f"Row {row.idx}: {exc}")
        row.total_required_qty = source.qty
        row.project_previous_qty = previous
        row.previous_qty = party_done.get(source.name, 0)
        row.total_executed_qty = row.previous_qty + current
        row.qty_percentage = current/(float(source.qty)-previous)*100 if float(source.qty) > previous else 0
        positive = positive or current > 0
    return positive


def validate_clearance(doc):
    if not doc.get("project"):
        frappe.throw("Select Project first")
    lock_project(doc.project)
    buying = doc.doctype == "Subcontract Clearnce"
    subcontract = buying and doc.get("subcontractor_contract")
    if subcontract:
        from contractor.subcontracting import contract_sources
        project, contract = contract_sources(doc.subcontractor_contract)
        if project.name != doc.project or contract.supplier != doc.get("supplier"):
            frappe.throw("Project and Supplier must match the Subcontractor Contract")
        doc.project_contract = project.get("project_contract")
        doc.tender_analysis = project.get("tender_analysis")
        doc.project_offer = project.get("project_offer")
    else:
        project, contract = sources(doc.project)
        doc.project_contract = contract.name
        doc.tender_analysis = contract.tender_analysis
        doc.project_offer = contract.get("project_offer")
    doc.title = doc.get("title") or project.project_name
    doc.company = doc.get("company") or contract.company
    doc.currency = doc.get("currency") or contract.currency
    doc.conversion_rate = doc.get("conversion_rate") or contract.conversion_rate
    doc.posting_date = doc.get("posting_date") or today()
    doc.transaction_date = doc.posting_date
    if doc.company != contract.company or doc.currency != contract.currency:
        frappe.throw("Company and currency must match the source contract")
    if buying:
        if not doc.get("supplier"):
            frappe.throw("Select Supplier")
    else:
        doc.customer = doc.get("customer") or contract.customer
        if doc.customer != contract.customer:
            frappe.throw("Customer must match the Project Contract")
    old = doc.get_doc_before_save()
    for field in ("invoice", "invoice_doctype", "deduction_entry"):
        if doc.get(field) and (not old or doc.get(field) != old.get(field)):
            frappe.throw("Accounting references are managed by certificate submission")
    positive = set_quantities(doc, project)
    if doc.docstatus == 1 and not positive:
        frappe.throw("Enter a positive current-period quantity before submitting")
    project_rows = {row.name: row for row in project.project_clauses}
    for row in doc.clauses:
        if row.is_group:
            continue
        if buying:
            if doc.docstatus == 1 and row.qty and flt(row.rate) <= 0:
                frappe.throw(f"Row {row.idx}: enter the subcontractor's unit rate")
        else:
            row.rate = contract_row(project_rows[row.project_clause_ref], contract).rate
    from contractor.project_contract_taxes import calculate_contract_taxes
    calculate_contract_taxes(doc)
    for row in doc.deductions:
        if frappe.get_cached_value("Account", row.account, "company") != doc.company:
            frappe.throw("Deduction accounts must belong to the certificate company")
        row.value = flt(row.value, doc.precision("total_deductions"))
    doc.total_deductions = sum(flt(row.value) for row in doc.deductions)
    doc.base_total_deductions = flt(doc.total_deductions * doc.conversion_rate, doc.precision("base_total_deductions"))
    doc.net_payable = flt(doc.grand_total-doc.total_deductions, doc.precision("net_payable"))
    doc.status = "Submitted" if doc.docstatus == 1 else "Draft"


def submit_clearance(doc):
    from contractor.clearance_accounting import post_accounting
    post_accounting(doc)
    refresh_project(doc.project)


def cancel_clearance(doc):
    from contractor.clearance_accounting import cancel_accounting
    cancel_accounting(doc)
    doc.db_set("status", "Cancelled", update_modified=False)
    refresh_project(doc.project)


@frappe.whitelist()
def preview(doc):
    data = frappe.parse_json(doc)
    if data.get("doctype") not in CERTIFICATES:
        frappe.throw("Unsupported certificate type")
    candidate = frappe.get_doc(data)
    if candidate.is_new():
        candidate.check_permission("create")
    else:
        frappe.get_doc(candidate.doctype, candidate.name).check_permission("write")
    if candidate.docstatus != 0 or candidate.get("legacy_record"):
        frappe.throw("Only draft clause certificates can be recalculated")
    validate_clearance(candidate)
    return candidate


@frappe.whitelist()
def deduction_template(template, company, buying=0):
    doctype = "Purchasing Deductions Template" if str(buying) in ("1", "True", "true") else "Selling Deductions Template"
    doc = frappe.get_doc(doctype, template)
    doc.check_permission("read")
    from contractor.deductions import validate_accounts
    validate_accounts(doc.deductions, company)
    return [copy_child_values(row) for row in doc.deductions]
