import io

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from contractor.tender_logic import number_rows
from contractor.clause_excel import HEADERS, read_clause_excel


class TenderAnalysis(Document):
    def validate(self):
        from contractor.tender_pricing import submitted_boq_links
        linked = submitted_boq_links(self) if not self.is_new() else {}
        for row in self.clauses:
            row.submitted_boq = linked.get(row.name)
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
        from contractor.deductions import update_tender_deductions
        update_tender_deductions(self)
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
    for key in ("tender_number", "party_type", "party_name", "currency", "numbering_mode", "project"):
        note.set(key, tender.get(key))
    note.tender_analysis = tender.name
    for row in tender.clauses:
        note.append("costing_note_items", dict(contractual_clause=row.contractual_clause,
            clause_title=row.clause_title, source_row=row.name, is_group=row.is_group,
            series_number=row.series_number, parent_series=row.parent_series,
            qty=row.qty, uom=row.uom))
    return note





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
    doc = frappe.get_doc("Tender Analysis", tender_analysis)
    doc.check_permission("write")
    return read_clause_excel(file_url)




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
