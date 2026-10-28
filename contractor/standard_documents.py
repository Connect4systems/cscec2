"""Restore native ERPNext trading documents while preserving stored field values."""
import json
from pathlib import Path

import frappe
from frappe.utils import now

NATIVE_DOCUMENTS = {
    'Opportunity': 'crm', 'Opportunity Item': 'crm',
    'Quotation': 'selling', 'Quotation Item': 'selling',
    'Sales Order': 'selling', 'Sales Order Item': 'selling',
    'Sales Invoice': 'accounts', 'Sales Invoice Item': 'accounts',
    'Purchase Order': 'buying', 'Purchase Order Item': 'buying',
    'Purchase Invoice': 'accounts', 'Purchase Invoice Item': 'accounts',
    'Purchase Receipt': 'stock', 'Purchase Receipt Item': 'stock',
    'Sales Taxes and Charges': 'accounts', 'Purchase Taxes and Charges': 'accounts',
}


def restore_standard_documents():
    manifest = json.loads((Path(__file__).parent / 'patches/standard_erpnext_documents.json').read_text())
    result = {'removed_fields': [], 'removed_setters': [], 'removed_links': [], 'retained': []}
    for field in manifest['fields']:
        record = frappe.db.get_value('Custom Field', field, ['name', 'module'], as_dict=True)
        if not record:
            continue
        if record.module and record.module != 'Contractor App':
            result['retained'].append(f"{record.name}: owned by {record.module}")
            continue
        if frappe.db.exists('Workflow', {'document_type': field['dt'], 'is_active': 1,
                'workflow_state_field': field['fieldname']}):
            result['retained'].append(f"{record.name}: required by an active site Workflow")
            continue
        # Delete metadata only: Custom Field deletion leaves its SQL column/values intact.
        frappe.delete_doc('Custom Field', record.name)
        result['removed_fields'].append(record.name)
    for expected in manifest['setters']:
        record = frappe.db.get_value('Property Setter', expected['name'],
            ['doc_type', 'field_name', 'property'], as_dict=True)
        if record and all(record.get(key) == expected.get(key) for key in ('doc_type', 'field_name', 'property')):
            frappe.delete_doc('Property Setter', expected['name'])
            result['removed_setters'].append(expected['name'])
    for expected in manifest['links']:
        record = frappe.db.get_value('DocType Link', expected['name'],
            ['parent', 'link_doctype'], as_dict=True)
        if record and all(record.get(key) == expected.get(key) for key in ('parent', 'link_doctype')):
            frappe.db.delete('DocType Link', {'name': expected['name']})
            result['removed_links'].append(expected['name'])
    # Also remove any app-owned setters still addressing the app's removed fields.
    for field in manifest['fields']:
        if frappe.db.exists('Custom Field', field):
            continue
        for setter in frappe.get_all('Property Setter', filters={
                'doc_type': field['dt'], 'field_name': field['fieldname']}, fields=['name']):
            frappe.delete_doc('Property Setter', setter.name)
    for doctype, module in NATIVE_DOCUMENTS.items():
        frappe.reload_doc(module, 'doctype', frappe.scrub(doctype), force=True)
        frappe.db.set_value('DocType', doctype, 'modified', now(), update_modified=False)
        frappe.clear_cache(doctype=doctype)
    for reason in result['retained']:
        print('Retained site configuration: ' + reason)
    return result
