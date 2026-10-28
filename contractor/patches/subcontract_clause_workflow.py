"""Sync subcontract clause forms and keep historical contract type links valid."""
import frappe


def execute():
    for slug in ('subcontractor_contract_clause', 'subcontractor_contract', 'cr', 'clearnce_clause', 'subcontract_clearnce'):
        frappe.reload_doc('contractor_app', 'doctype', slug, force=True)
    from contractor.patches.cr_contract_types import execute as seed_types
    seed_types()
    for row in frappe.get_all('Subcontractor Contract', fields=['contract_type'], distinct=True):
        if row.contract_type and not frappe.db.exists('Contract Type', row.contract_type):
            frappe.get_doc({'doctype': 'Contract Type', 'title': row.contract_type}).insert(ignore_permissions=True)
    for row in frappe.get_all('Property Setter', filters={
            'doc_type': 'Subcontractor Contract', 'field_name': 'contract_type',
            'property': ['in', ['options', 'link_filters']]}, fields=['name']):
        frappe.delete_doc('Property Setter', row.name)
    frappe.clear_cache()
