import io
import zipfile

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from contractor.tender_logic import number_rows


class TenderAnalysis(Document):
    def validate(self):
        try:
            number_rows(self.clauses, self.numbering_mode)
        except ValueError as exc:
            frappe.throw(str(exc))
        seen = set()
        group = None
        self.total_amount = 0
        for row in self.clauses:
            if row.contractual_clause:
                clause = frappe.get_doc("Contractual Clause", row.contractual_clause)
                if (clause.tender_analysis != self.name or clause.source_row != row.name
                        or bool(clause.is_group) != bool(row.is_group)):
                    frappe.throw(f"Row {row.idx}: clause reference or group type does not match")
                if clause.name in seen:
                    frappe.throw("A Contractual Clause cannot appear twice")
                seen.add(clause.name)
            if row.is_group:
                group = row
                row.rate = row.amount = 0
            else:
                row.amount = flt(row.qty) * flt(row.rate)
                group.amount += row.amount
                self.total_amount += row.amount
        old = self.get_doc_before_save()
        if old:
            old_rows = {r.name: r for r in old.clauses}
            current = {r.name: r for r in self.clauses}
            for name, before in old_rows.items():
                after = current.get(name)
                if before.applied_costing_note and (not after or after.qty != before.qty
                        or after.is_group != before.is_group
                        or after.contractual_clause != before.contractual_clause):
                    frappe.throw("Cancel the applied Costing Note before changing priced clause quantities or removing clauses")

    def on_update(self):
        for row in self.clauses:
            if row.contractual_clause:
                clause = frappe.get_doc("Contractual Clause", row.contractual_clause)
                if clause.title != row.clause_title:
                    clause.title = row.clause_title
                    clause.save()


@frappe.whitelist()
def create_contractual_clauses(tender_analysis):
    doc = frappe.get_doc("Tender Analysis", tender_analysis)
    doc.check_permission("write")
    # Serialize repeated clicks and concurrent requests for this tender.
    frappe.db.sql("select name from `tabTender Analysis` where name=%s for update", doc.name)
    doc.reload()
    if not doc.clauses:
        frappe.throw("Add or upload Contractual Clauses first")
    for row in doc.clauses:
        if not row.contractual_clause:
            existing = frappe.db.get_value("Contractual Clause", {"source_row": row.name}, "name")
            if existing:
                row.contractual_clause = existing
            else:
                clause = frappe.get_doc(dict(doctype="Contractual Clause", title=row.clause_title,
                    tender_analysis=doc.name, is_group=row.is_group, source_row=row.name)).insert()
                row.contractual_clause = clause.name
    doc.save()
    return doc.name


@frappe.whitelist()
def create_costing_note(tender_analysis):
    tender = frappe.get_doc("Tender Analysis", tender_analysis)
    tender.check_permission("read")
    if not tender.clauses or any(not r.contractual_clause for r in tender.clauses):
        frappe.throw("Create all Contractual Clauses first")
    note = frappe.new_doc("Costing Note")
    note.check_permission("create")
    for key in ("tender_number", "party_type", "party_name", "currency", "numbering_mode"):
        note.set(key, tender.get(key))
    note.tender_analysis = tender.name
    for row in tender.clauses:
        note.append("costing_note_items", dict(contractual_clause=row.contractual_clause,
            clause_title=row.clause_title, source_row=row.name, is_group=row.is_group,
            series_number=row.series_number, parent_series=row.parent_series,
            qty=row.qty, uom=row.uom))
    return note


HEADERS = ["Series Number", "Contractual Clause Title", "Is Group", "Qty", "UOM"]


@frappe.whitelist()
def download_template():
    from openpyxl import Workbook
    frappe.has_permission("Tender Analysis", "read", throw=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Contractual Clauses"
    sheet.append(HEADERS)
    sheet.append(["1", "Civil Works", 1, None, None])
    sheet.append(["1_1", "Excavation", 0, 100, None])
    output = io.BytesIO()
    workbook.save(output)
    frappe.local.response.filename = "tender_clauses.xlsx"
    frappe.local.response.filecontent = output.getvalue()
    frappe.local.response.type = "binary"


@frappe.whitelist()
def preview_excel(tender_analysis, file_url):
    from openpyxl import load_workbook
    doc = frappe.get_doc("Tender Analysis", tender_analysis)
    doc.check_permission("write")
    file = frappe.get_doc("File", {"file_url": file_url})
    file.check_permission("read")
    content = file.get_content()
    if len(content) > 5 * 1024 * 1024:
        frappe.throw("Excel file must be no larger than 5 MB")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if sum(entry.file_size for entry in archive.infolist()) > 30 * 1024 * 1024:
                frappe.throw("Excel workbook is too large when expanded")
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
        sheet = workbook.active
        records = sheet.iter_rows(values_only=True)
        if list(next(records, ()))[:5] != HEADERS:
            frappe.throw("Use the provided Excel template and its column headings")
        rows = []
        for index, values in enumerate(records, 2):
            if index > 10002:
                frappe.throw("Maximum 10,000 Excel rows")
            if not any(v is not None for v in values):
                continue
            values = list(values[:5]) + [None] * max(0, 5-len(values))
            series, title, flag, qty, uom = values
            if any(isinstance(v, str) and v.startswith("=") for v in values):
                frappe.throw(f"Excel row {index}: formulas are not supported")
            if str(flag or 0).lower() not in ("0", "1", "yes", "no", "true", "false"):
                frappe.throw(f"Excel row {index}: Is Group must be 0 or 1")
            if isinstance(series, (float, int)) and float(series).is_integer():
                series = str(int(series))
            row = dict(series_number=str(series or ""), clause_title=str(title or ""),
                is_group=int(str(flag).lower() in ("1", "yes", "true")), qty=float(qty or 0), uom=uom)
            if uom and not frappe.db.exists("UOM", uom):
                frappe.throw(f"Excel row {index}: unknown UOM {uom}")
            rows.append(row)
        number_rows(rows, "From Excel")
        if not rows:
            frappe.throw("The spreadsheet has no clauses")
        return rows
    except (ValueError, TypeError, zipfile.BadZipFile) as exc:
        frappe.throw(str(exc))
    finally:
        if "workbook" in locals():
            workbook.close()


@frappe.whitelist()
def apply_excel(tender_analysis, file_url):
    doc = frappe.get_doc("Tender Analysis", tender_analysis)
    doc.check_permission("write")
    if any(r.contractual_clause for r in doc.clauses):
        frappe.throw("Excel replacement is available only before Contractual Clauses are created")
    rows = preview_excel(tender_analysis, file_url)
    doc.set("clauses", rows)
    doc.numbering_mode = "From Excel"
    doc.save()
    return doc.name
