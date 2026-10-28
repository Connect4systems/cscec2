"""Build and validate cost-budget snapshots from a submitted Project Contract."""
import frappe
from frappe.utils import today

from contractor.project_budget_rules import build_budget, amounts_match, UNIT_FIELDS
from contractor.boq_quantities import unit_costs

SOURCE_FIELDS = ('contract_clause_row', 'source_row', 'contractual_clause', 'is_group',
    'series_number', 'parent_series', 'clause_title', 'qty', 'uom', 'costing_note', 'costing_note_row', 'boq')


def contract_source(project_contract):
    contract = frappe.get_doc('Project Contract', project_contract)
    contract.check_permission('read')
    if contract.docstatus != 1:
        frappe.throw('Submit the Project Contract before creating a Project Budget')
    project_name = contract.get('created_project') or frappe.db.get_value('Project', {'project_contract': contract.name}, 'name')
    if not project_name:
        frappe.throw('Create the operational Project from the Project Contract first')
    project = frappe.get_doc('Project', project_name)
    project.check_permission('read')
    if project.get('project_contract') != contract.name or project.company != contract.company:
        frappe.throw('The Project does not belong to this Project Contract/company')
    if project.status == 'Cancelled':
        frappe.throw('Cannot create a budget for a cancelled Project')
    return contract, project


def active_budget(project_contract, exclude=None):
    filters = {'project_contract': project_contract, 'docstatus': ['!=', 2]}
    if exclude:
        filters['name'] = ['!=', exclude]
    return frappe.db.get_value('Project Budget', filters, 'name')


def source_rows(contract, precision=2):
    tender = frappe.get_doc('Tender Analysis', contract.tender_analysis)
    tender.check_permission('read')
    if tender.company != contract.company or tender.currency != contract.currency:
        frappe.throw('Budget company/currency must match its tender and contract')
    tender_rows = {row.name: row for row in tender.clauses}
    notes, boqs, linked, identities = {}, {}, {}, {}
    for row in contract.clauses:
        original = tender_rows.get(row.source_row)
        if (not original or original.contractual_clause != row.contractual_clause
                or bool(original.is_group) != bool(row.is_group)):
            frappe.throw(f'Clause {row.series_number}: source Tender Analysis row does not match')
        if row.is_group:
            continue
        if not row.get('costing_note'):
            frappe.throw(f'Clause {row.series_number}: missing Costing Note')
        if row.costing_note not in notes:
            note = frappe.get_doc('Costing Note', row.costing_note)
            note.check_permission('read')
            notes[row.costing_note] = note
        note = notes[row.costing_note]
        if note.docstatus != 1 or note.tender_analysis != contract.tender_analysis or note.currency != contract.currency:
            frappe.throw(f'Clause {row.series_number}: matching Costing Note must be submitted')
        matches = [item for item in note.costing_note_items if item.source_row == row.source_row
            and item.contractual_clause == row.contractual_clause and not item.is_group]
        if len(matches) != 1:
            frappe.throw(f'Clause {row.series_number}: cannot uniquely match the Costing Note row')
        note_row = matches[0]
        boq_name = row.get('submitted_boq') or note_row.get('boq_reference')
        if not boq_name:
            candidates = frappe.get_all('BOQ', filters={'costing_note': note.name, 'line_id': note_row.name,
                'tender_analysis': contract.tender_analysis, 'contractual_clause': row.contractual_clause,
                'docstatus': 1}, pluck='name', limit_page_length=2)
            if len(candidates) != 1:
                frappe.throw(f'Clause {row.series_number}: select one matching submitted BOQ on the contract')
            boq_name = candidates[0]
        if boq_name not in boqs:
            boq = frappe.get_doc('BOQ', boq_name)
            boq.check_permission('read')
            boqs[boq_name] = boq
        boq = boqs[boq_name]
        if (boq.docstatus != 1 or boq.costing_note != note.name or boq.line_id != note_row.name
                or boq.tender_analysis != contract.tender_analysis or boq.contractual_clause != row.contractual_clause):
            frappe.throw(f'Clause {row.series_number}: BOQ does not match the submitted costing source')
        if row.get('uom') != note_row.get('uom') or row.get('uom') != boq.get('unit'):
            frappe.throw(f'Clause {row.series_number}: contract/Costing Note/BOQ units do not match')
        try:
            units = unit_costs(boq)
            if boq.get('quantity_basis') == 'Project Quantity' and not amounts_match(boq.project_qty, note_row.qty, 6):
                frappe.throw(f'Clause {row.series_number}: BOQ Project Quantity differs from its Costing Note')
            if not amounts_match(note_row.cost, units['total_cost'], precision):
                frappe.throw(f'Clause {row.series_number}: Costing Note unit cost does not match its BOQ')
        except ValueError as exc:
            frappe.throw(str(exc))
        linked[row.name] = units
        identities[row.name] = {'costing_note': note.name, 'costing_note_row': note_row.name}
    try:
        rows, totals = build_budget(contract.clauses, linked, precision)
    except ValueError as exc:
        frappe.throw(str(exc))
    for row in rows:
        row.update(identities.get(row['contract_clause_row'], {}))
    return rows, totals


@frappe.whitelist()
def create_budget(project_contract):
    # Saving a mapped draft takes this same lock before enforcing uniqueness.
    frappe.db.sql('select name from `tabProject Contract` where name=%s for update', project_contract)
    contract, project = contract_source(project_contract)
    existing = active_budget(contract.name)
    if existing:
        frappe.get_doc('Project Budget', existing).check_permission('read')
        return {'existing': existing}
    doc = frappe.new_doc('Project Budget')
    doc.check_permission('create')
    doc.update(dict(project_contract=contract.name, project=project.name, tender_analysis=contract.tender_analysis,
        title=contract.title, company=contract.company, currency=contract.currency,
        posting_date=today(), status='Draft'))
    rows, totals = source_rows(contract, doc.precision('total_project_budget') or 2)
    doc.set('clauses', rows)
    doc.update(totals)
    return {'doc': doc}


def validate_budget(doc):
    frappe.db.sql('select name from `tabProject Contract` where name=%s for update', doc.project_contract)
    old = doc.get_doc_before_save()
    if old and old.project_contract != doc.project_contract:
        frappe.throw('The source Project Contract cannot be changed')
    contract, project = contract_source(doc.project_contract)
    if active_budget(contract.name, exclude=doc.name):
        frappe.throw('An active Project Budget already exists for this Project Contract')
    precision = doc.precision('total_project_budget') or 2
    expected, totals = source_rows(contract, precision)
    # A draft must not silently adopt different costing sources or costs on later saves.
    if old:
        if len(old.clauses) != len(expected):
            frappe.throw('Budget sources changed; recreate the draft budget')
        for before, after in zip(old.clauses, expected):
            for field in SOURCE_FIELDS + UNIT_FIELDS:
                left, right = before.get(field), after.get(field)
                if field in UNIT_FIELDS or field == 'qty':
                    if not amounts_match(left, right, 6):
                        frappe.throw('Budget source quantities or costs changed; recreate the draft budget')
                elif (left or '') != (right or ''):
                    frappe.throw('Budget sources changed; recreate the draft budget')
    if not doc.get('clauses') and doc.is_new():
        doc.set('clauses', expected)
    elif len(doc.clauses) != len(expected):
        frappe.throw('The budget must contain every Project Contract clause')
    for row, values in zip(doc.clauses, expected):
        if row.get('contract_clause_row') != values['contract_clause_row']:
            frappe.throw('Budget clause rows must match the Project Contract in order')
        row.update(values)
    doc.update(totals)
    doc.update(dict(project=project.name, tender_analysis=contract.tender_analysis,
        title=contract.title, company=contract.company, currency=contract.currency,
        status='Submitted' if doc.docstatus == 1 else 'Draft'))
