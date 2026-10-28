"""Seed CR Contract Types and preserve names used by existing CRs."""
import frappe

CONTRACT_TYPES = ('Arch', 'Civil', 'Elec', 'Mech', 'Service')


def execute():
    # Keep historical CR values valid after switching their Link target.
    titles = set(CONTRACT_TYPES)
    for row in frappe.get_all('CR', fields=['contract_type'], distinct=True):
        if row.contract_type:
            titles.add(row.contract_type)
    for title in sorted(titles):
        if not frappe.db.exists('Contract Type', title):
            frappe.get_doc({'doctype': 'Contract Type', 'title': title}).insert(ignore_permissions=True)
    # Remove the former Item Group filter if a site customization retained it.
    for setter in frappe.get_all('Property Setter', filters={
            'doc_type': 'CR', 'field_name': 'contract_type',
            'property': ['in', ['options', 'link_filters']]}, fields=['name']):
        frappe.delete_doc('Property Setter', setter.name)
    frappe.clear_cache(doctype='CR')
