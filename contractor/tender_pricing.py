"""Costing Note and BOQ integration for Tender Analysis."""
import frappe
from frappe.utils import flt, today

from contractor.tender_logic import number_rows, price_rows


def validate_note(note):
    if any(note.get(key) for key in ("opportunity", "sales_order", "purchase_order", "project")):
        frappe.throw("A tender Costing Note cannot also price another document")
    tender = frappe.get_doc("Tender Analysis", note.tender_analysis)
    tender.check_permission("read")
    source = {r.name: r for r in tender.clauses}
    seen = set()
    if len(note.costing_note_items) != len(source):
        frappe.throw("The tender clause list has changed; recreate the Costing Note")
    for row, original in zip(note.costing_note_items, tender.clauses):
        match = source.get(row.source_row)
        if (not match or row.source_row in seen or match.name != original.name
                or match.contractual_clause != row.contractual_clause or not row.contractual_clause
                or bool(match.is_group) != bool(row.is_group) or flt(match.qty) != flt(row.qty)
                or match.uom != row.uom):
            frappe.throw(f"Row {row.idx}: source clause has changed; recreate the Costing Note")
        seen.add(row.source_row)
        row.clause_title = match.clause_title
        row.series_number = match.series_number
        row.parent_series = match.parent_series
    try:
        number_rows(note.costing_note_items, tender.numbering_mode)
        cost, selling = price_rows(note.costing_note_items)
    except ValueError as exc:
        frappe.throw(str(exc))
    note.total_cost = cost
    note.total_target_selling_price = selling
    note.total_profit = selling - cost
    note.profit_margin = (selling-cost) / cost * 100 if cost else 0
    note.set("group_items", [])


def apply_note(note, cancel=False):
    # Lock the tender so concurrent submissions cannot both claim its prices.
    frappe.db.sql("select name from `tabTender Analysis` where name=%s for update", note.tender_analysis)
    tender = frappe.get_doc("Tender Analysis", note.tender_analysis)
    tender.check_permission("write")
    source = {r.name: r for r in tender.clauses}
    for row in note.costing_note_items:
        if row.is_group:
            continue
        target = source.get(row.source_row)
        if not target or target.contractual_clause != row.contractual_clause or flt(target.qty) != flt(row.qty):
            frappe.throw("A priced source clause has changed; pricing cannot be applied")
        if cancel:
            if target.applied_costing_note != note.name:
                frappe.throw("This Costing Note no longer owns the clause pricing")
            if flt(target.rate) != flt(row.applied_rate):
                frappe.throw("Clause pricing was edited after submission")
            target.rate = row.previous_rate
            target.applied_costing_note = row.previous_costing_note
        else:
            if target.applied_costing_note:
                frappe.throw("Cancel the previous Costing Note before applying new pricing")
            rate = flt(flt(row.target_selling_price) / flt(row.qty), target.precision("rate"))
            row.db_set("previous_rate", target.rate or 0, update_modified=False)
            row.db_set("previous_costing_note", target.applied_costing_note, update_modified=False)
            row.db_set("applied_rate", rate, update_modified=False)
            target.rate = rate
            target.applied_costing_note = note.name
    tender.save()


@frappe.whitelist()
def create_clause_boq(costing_note, row_name):
    note = frappe.get_doc("Costing Note", costing_note)
    note.check_permission("write")
    if not note.tender_analysis or note.docstatus != 0:
        frappe.throw("BOQ pricing requires a draft tender Costing Note")
    row = next((r for r in note.costing_note_items if r.name == row_name), None)
    if not row or row.is_group or not row.contractual_clause:
        frappe.throw("Select a detail Contractual Clause")
    existing = frappe.db.get_value("BOQ", {"costing_note": note.name, "line_id": row.name, "docstatus": ["<", 2]}, "name")
    if existing:
        frappe.get_doc("BOQ", existing).check_permission("read")
        return {"existing": existing}
    boq = frappe.new_doc("BOQ")
    boq.check_permission("create")
    boq.update(dict(naming_series="BOQ-.YYYY.-", tender_analysis=note.tender_analysis,
        contractual_clause=row.contractual_clause, unit=row.uom, project_qty=row.qty,
        party_type=note.party_type, party_name=note.party_name, start_date=today(),
        costing_note=note.name, line_id=row.name))
    return {"doc": boq}


def update_from_boq(boq, cancel=False):
    frappe.db.sql("select name from `tabCosting Note` where name=%s for update", boq.costing_note)
    note = frappe.get_doc("Costing Note", boq.costing_note)
    note.check_permission("write")
    if cancel and note.docstatus == 2:
        return
    if note.docstatus != 0:
        frappe.throw("Cancel or amend the Costing Note before changing its BOQ pricing")
    row = next((r for r in note.costing_note_items if r.name == boq.line_id), None)
    if (not row or row.is_group or row.contractual_clause != boq.contractual_clause
            or note.tender_analysis != boq.tender_analysis):
        frappe.throw("BOQ clause does not match its source Costing Note row")
    duplicates = frappe.db.exists("BOQ", {"costing_note": note.name, "line_id": row.name,
        "docstatus": 1, "name": ["!=", boq.name]})
    if duplicates:
        frappe.throw("Another submitted BOQ already prices this clause")
    row.cost = 0 if cancel else boq.total_cost
    note.save()
