"""Expose the Project abbreviation expected by existing document naming hooks."""
import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({'Project': [{
        'fieldname': 'custom_abbreviation',
        'fieldtype': 'Data',
        'label': 'Project Abbreviation',
        'insert_after': 'project_name',
        'allow_in_quick_entry': 1,
        'in_standard_filter': 1,
        'description': 'Short project code used in CR and subcontractor document numbering.',
        'hidden': 0,
        'read_only': 0,
        'reqd': 0,
        'permlevel': 0,
        'depends_on': None,
        'read_only_depends_on': None,
    }]}, update=True)
    # Site-level field overrides can hide an otherwise visible Custom Field.
    for setter in frappe.get_all('Property Setter', filters={
            'doc_type': 'Project', 'field_name': 'custom_abbreviation',
            'property': ['in', ['hidden', 'read_only', 'depends_on', 'permlevel', 'insert_after', 'label']]},
            fields=['name']):
        frappe.delete_doc('Property Setter', setter.name)
    for setter in frappe.get_all('Property Setter',
            filters={'doc_type': 'Project', 'property': 'field_order'}, fields=['name', 'value']):
        try:
            order = json.loads(setter.value)
        except (TypeError, ValueError):
            continue
        if not isinstance(order, list):
            continue
        original = list(order)
        order = [name for name in order if name != 'custom_abbreviation']
        position = order.index('project_name') + 1 if 'project_name' in order else 0
        order.insert(position, 'custom_abbreviation')
        if order != original:
            frappe.db.set_value('Property Setter', setter.name, 'value', json.dumps(order))
    # Invalidate browser metadata as well as the server cache.
    from frappe.utils import now
    frappe.db.set_value('DocType', 'Project', 'modified', now(), update_modified=False)
    frappe.clear_cache(doctype='Project')
