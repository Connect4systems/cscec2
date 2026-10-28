"""Expose the Project abbreviation expected by existing document naming hooks."""
import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({'Project': [{
        'fieldname': 'custom_abbreviation',
        'fieldtype': 'Data',
        'label': 'Abbreviation',
        'insert_after': 'project_name',
        'allow_in_quick_entry': 1,
        'in_standard_filter': 1,
        'description': 'Short project code used in CR and subcontractor document numbering.',
        'hidden': 0,
        'read_only': 0,
        'reqd': 0,
    }]}, update=True)
    for setter in frappe.get_all('Property Setter',
            filters={'doc_type': 'Project', 'property': 'field_order'}, fields=['name', 'value']):
        try:
            order = json.loads(setter.value)
        except (TypeError, ValueError):
            continue
        if not isinstance(order, list) or 'custom_abbreviation' in order:
            continue
        position = order.index('project_name') + 1 if 'project_name' in order else 0
        order.insert(position, 'custom_abbreviation')
        frappe.db.set_value('Property Setter', setter.name, 'value', json.dumps(order))
    frappe.clear_cache(doctype='Project')
