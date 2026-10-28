"""Purchasing commercial terms shared by CR, subcontract, and certificates."""
import math

import frappe
from frappe.utils import flt, today

from contractor.document_mapping import copy_child_values

COMMERCIAL_TYPES = ('CR', 'Subcontractor Contract')
COMMERCIAL_FIELDS = ('company', 'currency', 'conversion_rate', 'taxes_and_charges',
    'purchasing_deductions_template', 'apply_discount_on', 'additional_discount_percentage',
    'discount_amount', 'disable_rounded_total')


def copy_commercial_terms(source, target, clearance=False):
    for key in COMMERCIAL_FIELDS:
        if source.get(key) is not None:
            target.set(key, source.get(key))
    for table in ('taxes', 'deductions'):
        target.set(table, [])
        for row in source.get(table) or []:
            values = copy_child_values(row)
            if clearance and table == 'taxes' and row.get('charge_type') == 'Actual':
                values['tax_amount'] = 0  # Fixed charges belong to a period, not every certificate.
            if clearance and table == 'deductions':
                values['value'] = 0
            target.append(table, values)
    if clearance:
        target.discount_amount = 0  # Keep discount percentages; enter fixed period discounts explicitly.
    else:
        from contractor.project_contract_taxes import TOTAL_FIELDS
        for key in TOTAL_FIELDS + ('total_deductions', 'base_total_deductions', 'net_payable'):
            if source.get(key) is not None:
                target.set(key, source.get(key))


def calculate_commercial(doc, project=None, load_templates=True):
    if project is None:
        project = frappe.get_doc('Project', doc.project)
        project.check_permission('read')
    doc.company = doc.get('company') or project.company
    if doc.company != project.company:
        frappe.throw('Company must match the Project')
    base_currency = frappe.get_cached_value('Company', doc.company, 'default_currency')
    doc.currency = doc.get('currency') or base_currency
    if doc.currency == base_currency:
        doc.conversion_rate = 1
    elif not math.isfinite(flt(doc.get('conversion_rate'))) or flt(doc.get('conversion_rate')) <= 0:
        frappe.throw('Enter a positive currency conversion rate')
    doc.transaction_date = doc.get('posting_date') or doc.get('date') or today()
    from contractor.project_contract_taxes import calculate_contract_taxes, get_tax_template
    if load_templates:
        old = doc.get_doc_before_save()
        if (doc.get('taxes_and_charges') and not doc.get('taxes')
                and (not old or old.get('taxes_and_charges') != doc.taxes_and_charges)):
            doc.set('taxes', get_tax_template(doc.taxes_and_charges, doc.company, buying=1))
        if (doc.get('purchasing_deductions_template') and not doc.get('deductions')
                and (not old or old.get('purchasing_deductions_template') != doc.purchasing_deductions_template)):
            template = frappe.get_doc('Purchasing Deductions Template', doc.purchasing_deductions_template)
            template.check_permission('read')
            doc.set('deductions', [copy_child_values(row) for row in template.deductions])
    # Validate even manually edited rows and ensure the selected deduction template exists.
    if doc.get('purchasing_deductions_template'):
        frappe.get_doc('Purchasing Deductions Template', doc.purchasing_deductions_template).check_permission('read')
    for table, field in (('taxes', 'account_head'), ('deductions', 'account')):
        for row in doc.get(table) or []:
            account = row.get(field)
            if account and frappe.get_cached_value('Account', account, 'company') != doc.company:
                frappe.throw('Tax and deduction accounts must belong to the document company')
    calculate_contract_taxes(doc)
    if doc.doctype == 'Subcontractor Contract' and doc.get('clauses'):
        doc.contract_amount = doc.grand_total


@frappe.whitelist()
def preview(doc):
    data = frappe.parse_json(doc)
    if data.get('doctype') not in COMMERCIAL_TYPES:
        frappe.throw('Expected CR or Subcontractor Contract')
    candidate = frappe.get_doc(data)
    if candidate.is_new():
        candidate.check_permission('create')
    else:
        frappe.get_doc(candidate.doctype, candidate.name).check_permission('write')
    if candidate.docstatus != 0:
        frappe.throw('Only draft totals can be recalculated')
    calculate_commercial(candidate, load_templates=False)
    from contractor.project_contract_taxes import TOTAL_FIELDS, CLAUSE_AMOUNT_FIELDS, tax_values
    return dict(totals={key: candidate.get(key) for key in TOTAL_FIELDS + (
        'company', 'currency', 'conversion_rate', 'total_deductions', 'base_total_deductions',
        'net_payable', 'contract_amount')},
        clauses=[{key: row.get(key) for key in CLAUSE_AMOUNT_FIELDS} for row in candidate.clauses],
        taxes=[tax_values(row) for row in candidate.taxes],
        deductions=[dict(value=row.value) for row in candidate.deductions])
