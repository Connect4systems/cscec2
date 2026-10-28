"""CR-to-subcontract mapping and contract-backed supplier certificates."""
import math

import frappe
from frappe.utils import flt, today

from contractor.document_mapping import copy_child_values
from contractor.progress_rules import certificate_quantity, quantity


@frappe.whitelist()
def create_contract(cr):
    source = frappe.get_doc('CR', cr)
    source.check_permission('read')
    if source.docstatus != 1:
        frappe.throw('Approve and submit the CR before creating a Subcontractor Contract')
    existing = frappe.db.get_value('Subcontractor Contract', {'cr': source.name, 'docstatus': ['!=', 2]}, 'name')
    if existing:
        frappe.get_doc('Subcontractor Contract', existing).check_permission('read')
        return {'existing': existing}
    doc = frappe.new_doc('Subcontractor Contract')
    doc.check_permission('create')
    for key in ('project', 'supplier', 'contract_type', 'posting_date', 'end_date', 'attach_cr',
                'note', 'cr_comparison', 'numbering_mode', 'project_abbriviation'):
        doc.set(key, source.get(key))
    doc.update(dict(cr=source.name, date=source.posting_date, cr_date=source.posting_date,
        delivery_date=source.end_date, cr_attach=source.attach_cr, comparison=source.get('cr_comparison'),
        text_editor_uxta=source.get('note'),
        company=frappe.db.get_value('Project', source.project, 'company')))
    for row in source.get('clauses') or []:
        values = copy_child_values(row)
        values['source_cr_row'] = row.name
        doc.append('clauses', values)
    return doc


def validate_contract(doc):
    project = frappe.get_doc('Project', doc.project)
    project.check_permission('read')
    if project.status == 'Cancelled':
        frappe.throw('Cannot contract against a cancelled Project')
    doc.company = doc.get('company') or project.company
    if doc.company != project.company:
        frappe.throw('Company must match the Project')
    base_currency = frappe.get_cached_value('Company', doc.company, 'default_currency')
    doc.currency = doc.get('currency') or base_currency
    if doc.currency == base_currency:
        doc.conversion_rate = 1
    elif not math.isfinite(flt(doc.get('conversion_rate'))) or flt(doc.get('conversion_rate')) <= 0:
        frappe.throw('Enter a positive currency conversion rate')
    if doc.get('cr'):
        frappe.db.sql('select name from `tabCR` where name=%s for update', doc.cr)
        source = frappe.get_doc('CR', doc.cr)
        source.check_permission('read')
        if source.docstatus != 1:
            frappe.throw('The source CR must be approved and submitted')
        if source.project != doc.project or source.get('supplier') != doc.supplier:
            frappe.throw('Project and Supplier must match the source CR')
        others = frappe.get_all('Subcontractor Contract', filters={'cr': doc.cr, 'docstatus': ['!=', 2],
            'name': ['!=', doc.name]}, pluck='name', limit_page_length=1)
        if others:
            frappe.throw('An active Subcontractor Contract already exists for this CR')
        source_rows = {row.name for row in source.get('clauses') or []}
        if any(row.get('source_cr_row') and row.source_cr_row not in source_rows for row in doc.clauses):
            frappe.throw('A contract clause does not belong to the source CR')
    total = 0
    group = None
    for row in doc.get('clauses') or []:
        if row.is_group:
            row.rate = row.amount = 0
            group = row
            continue
        rate = flt(row.get('rate'))
        if not math.isfinite(rate) or rate < 0 or (doc.docstatus == 1 and rate <= 0):
            frappe.throw('Enter a positive unit rate for every contract detail before submitting')
        row.amount = flt(row.qty) * rate
        total += row.amount
        if group:
            group.amount += row.amount
    if doc.get('clauses'):
        doc.contract_amount = total


def contract_sources(name):
    contract = frappe.get_doc('Subcontractor Contract', name)
    contract.check_permission('read')
    if contract.docstatus != 1:
        frappe.throw('Approve and submit the Subcontractor Contract first')
    if not contract.get('clauses'):
        frappe.throw('The Subcontractor Contract has no clauses')
    project = frappe.get_doc('Project', contract.project)
    project.check_permission('read')
    if project.status == 'Cancelled':
        frappe.throw('Cannot certify a cancelled Project')
    return project, contract


@frappe.whitelist()
def create_clearance(subcontractor_contract):
    project, contract = contract_sources(subcontractor_contract)
    doc = frappe.new_doc('Subcontract Clearnce')
    doc.check_permission('create')
    doc.update(dict(subcontractor_contract=contract.name, project=project.name,
        project_contract=project.get('project_contract'), project_offer=project.get('project_offer'),
        tender_analysis=project.get('tender_analysis'), title=project.project_name,
        company=contract.company, currency=contract.currency, conversion_rate=contract.conversion_rate,
        supplier=contract.supplier, posting_date=today(), transaction_date=today(),
        delivery_date=contract.delivery_date, legacy_record=0, status='Draft', apply_discount_on='Net Total'))
    for row in contract.clauses:
        values = {key: row.get(key) for key in ('is_group', 'series_number', 'parent_series',
            'clause_title', 'contractual_clause', 'uom', 'rate')}
        values.update(subcontractor_contract_clause=row.name, project_clause_ref=row.get('project_clause'),
            total_required_qty=row.get("qty") or 0, qty=0)
        doc.append('clauses', values)
    set_contract_quantities(doc, project, contract)
    return doc


def set_contract_quantities(doc, project, contract=None):
    if contract is None:
        _, contract = contract_sources(doc.subcontractor_contract)
    if doc.project != contract.project or doc.supplier != contract.supplier:
        frappe.throw('Project and Supplier must match the Subcontractor Contract')
    if doc.company != contract.company or doc.currency != contract.currency:
        frappe.throw('Company and currency must match the Subcontractor Contract')
    filters = {'subcontractor_contract': contract.name, 'docstatus': 1}
    if doc.name:
        filters['name'] = ['!=', doc.name]
    parents = frappe.get_all('Subcontract Clearnce', filters=filters, pluck='name')
    done = {}
    if parents:
        for row in frappe.get_all('Clearnce Clause', filters={'parent': ['in', parents],
                'parenttype': 'Subcontract Clearnce', 'is_group': 0}, fields=['subcontractor_contract_clause', 'qty']):
            key = row.subcontractor_contract_clause
            done[key] = done.get(key, 0) + flt(row.qty)
    from contractor.project_progress import executed_quantities
    project_done = executed_quantities(project.name, 'Subcontract Clearnce', exclude=doc.name)
    project_rows = {row.name: row for row in project.get('project_clauses') or []}
    source_rows = {row.name: row for row in contract.clauses}
    seen = set()
    positive = False
    for row in doc.clauses:
        source = source_rows.get(row.get('subcontractor_contract_clause'))
        if not source or source.name in seen:
            frappe.throw('Each clearance clause must reference a unique row of this Subcontractor Contract')
        seen.add(source.name)
        for key in ('is_group', 'series_number', 'parent_series', 'clause_title', 'contractual_clause', 'uom', 'rate'):
            row.set(key, source.get(key))
        row.project_clause_ref = source.get('project_clause')
        if source.is_group:
            row.qty = row.rate = row.amount = 0
            continue
        previous = done.get(source.name, 0)
        try:
            current = quantity(row.qty)
            row.remaining_qty = certificate_quantity(source.qty, previous, current)
            if row.project_clause_ref:
                project_row = project_rows.get(row.project_clause_ref)
                if not project_row:
                    raise ValueError('The source Project clause no longer exists')
                certificate_quantity(project_row.qty, project_done.get(project_row.name, 0), current)
        except ValueError as exc:
            frappe.throw(f'Row {row.idx}: {exc}')
        row.total_required_qty = source.qty
        row.previous_qty = row.project_previous_qty = previous
        row.total_executed_qty = previous + current
        row.qty_percentage = current / (float(source.qty)-previous) * 100 if float(source.qty) > previous else 0
        positive = positive or current > 0
    return positive
