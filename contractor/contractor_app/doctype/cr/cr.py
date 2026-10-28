import frappe
from frappe.model.document import Document

from contractor.tender_logic import number_rows
from contractor.clause_excel import HEADERS, read_clause_excel


class CR(Document):
    def validate(self):
        try:
            number_rows(self.get("clauses") or [], self.get("numbering_mode") or "Automatic")
        except ValueError as exc:
            frappe.throw(str(exc))
        # Existing attachment-only requests can still be saved. New clause requests need a supplier.
        if self.get("clauses") and not self.get("supplier"):
            frappe.throw("Select a Supplier for the contract clauses")
        sources = None
        seen_project_rows = set()
        for row in self.get("clauses") or []:
            if not row.get("project_clause"):
                if row.get("contractual_clause"):
                    frappe.throw("Contractual Clause references must come from the selected Project")
                continue
            if row.project_clause in seen_project_rows:
                frappe.throw("A Project clause can only appear once")
            seen_project_rows.add(row.project_clause)
            if sources is None:
                project = frappe.get_doc("Project", self.project)
                project.check_permission("read")
                sources = {r.name: r for r in project.get("project_clauses") or []}
            source = sources.get(row.project_clause)
            if not source or source.get("contractual_clause") != row.get("contractual_clause") or bool(source.is_group) != bool(row.is_group):
                frappe.throw("A fetched clause does not belong to the selected Project or its group type changed")

        if self.get("doctype") == "CR":
            from contractor.subcontract_commercial import calculate_commercial
            calculate_commercial(self)

    def before_cancel(self):
        frappe.db.sql("select name from `tabCR` where name=%s for update", self.name)
        if frappe.db.exists("Subcontractor Contract", {"cr": self.name, "docstatus": ["!=", 2]}):
            frappe.throw("Cancel or delete linked Subcontractor Contracts before cancelling the CR")


def editable_cr(cr, document_type="CR"):
    if document_type not in ("CR", "Subcontractor Contract"):
        frappe.throw("Unsupported clause document")
    doc = frappe.get_doc(document_type, cr)
    doc.check_permission("write")
    if doc.docstatus != 0:
        frappe.throw("Only draft documents can edit contract clauses")
    return doc


@frappe.whitelist()
def download_template(document_type="CR"):
    if document_type not in ("CR", "Subcontractor Contract"):
        frappe.throw("Unsupported clause document")
    frappe.has_permission(document_type, "read", throw=True)
    # Same format as Tender Analysis, with CR permissions.
    import io
    from openpyxl import Workbook
    workbook = Workbook()
    workbook.active.append(HEADERS)
    workbook.active.append(["1", "Civil Works", 1, None, None])
    workbook.active.append(["1_1", "Excavation", 0, 100, None])
    output = io.BytesIO()
    workbook.save(output)
    frappe.local.response.filename = "cr_clauses.xlsx"
    frappe.local.response.filecontent = output.getvalue()
    frappe.local.response.type = "binary"


@frappe.whitelist()
def preview_excel(cr, file_url, document_type="CR"):
    editable_cr(cr, document_type)
    return read_clause_excel(file_url)


@frappe.whitelist()
def apply_excel(cr, file_url, document_type="CR"):
    doc = editable_cr(cr, document_type)
    doc.set("clauses", read_clause_excel(file_url))
    doc.numbering_mode = "From Excel"
    doc.save()
    return doc.name


@frappe.whitelist()
def fetch_project_clauses(cr, fetch_all=1, selected_rows=None, project=None, quantities=None, document_type="CR"):
    doc = editable_cr(cr, document_type)
    if project and project != doc.project:
        frappe.throw("The CR Project changed. Reopen Fetch from Project.")
    project = frappe.get_doc("Project", doc.project)
    project.check_permission("read")
    rows = project.get("project_clauses") or []
    if not rows:
        frappe.throw("The selected Project has no contract clauses")
    from contractor.cr_clause_selection import select_project_rows, selected_quantities, merge_project_clauses
    if isinstance(selected_rows, str):
        selected_rows = frappe.parse_json(selected_rows)
    if isinstance(quantities, str):
        quantities = frappe.parse_json(quantities)
    try:
        rows = select_project_rows(rows, str(fetch_all).lower() in ('1', 'true'), selected_rows)
        overrides = selected_quantities(rows, quantities) if str(fetch_all).lower() not in ('1', 'true') else {}
    except ValueError as exc:
        frappe.throw(str(exc))
    incoming = []
    for row in rows:
        values = {key: row.get(key) for key in (
            "is_group", "series_number", "parent_series", "clause_title", "qty", "uom", "contractual_clause")}
        if row.name in overrides:
            values["qty"] = overrides[row.name]
        values["project_clause"] = row.name
        incoming.append(values)
    existing = list(doc.get("clauses") or [])
    try:
        if existing:
            number_rows(existing, doc.get("numbering_mode") or "Automatic")
        merged = merge_project_clauses(existing, incoming)
    except ValueError as exc:
        frappe.throw(str(exc))
    ordered = [doc.append("clauses", row) if isinstance(row, dict) else row for row in merged]
    # Retain existing child documents and their names, quantities, and other edits.
    doc.clauses[:] = ordered
    for index, row in enumerate(doc.clauses, 1):
        row.idx = index
    doc.numbering_mode = "From Excel"
    doc.save()
    return doc.name


@frappe.whitelist()
def project_clause_options(cr, document_type="CR"):
    doc = editable_cr(cr, document_type)
    project = frappe.get_doc("Project", doc.project)
    project.check_permission("read")
    return {"project": doc.project, "clauses": [
        {key: row.get(key) for key in (
            "name", "is_group", "series_number", "parent_series", "clause_title", "qty", "uom")}
        for row in project.get("project_clauses") or []]}
