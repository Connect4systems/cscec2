"""Retire audited unused metadata without deleting stored business data."""
import json
from pathlib import Path

import frappe


def execute():
    from contractor.app_cleanup import retire_unused_doctypes
    for result in retire_unused_doctypes():
        if result.get('removed'):
            print(f"Removed unused DocType metadata: {result['doctype']}")
        elif result['exists']:
            print(f"Retained {result['doctype']}: {'; '.join(result['reasons'])}")
    fields = json.loads(Path(__file__).with_name('retired_cycle_fields.json').read_text())
    for field in fields:
        name = frappe.db.get_value('Custom Field', field, 'name')
        if name:
            frappe.db.set_value('Custom Field', name,
                {'hidden': 1, 'in_list_view': 0, 'reqd': 0})
    # Only remove app-exported setters when their former target field is absent.
    meta = frappe.get_meta('BOQ ID')
    for name, field, property_name in (
            ('BOQ ID-item-label', 'item', 'label'),
            ('BOQ ID-naming_series-options', 'naming_series', 'options')):
        setter = frappe.db.get_value('Property Setter', name,
            ['doc_type', 'field_name', 'property'], as_dict=True)
        if (setter and setter.doc_type == 'BOQ ID' and setter.field_name == field
                and setter.property == property_name and not meta.has_field(field)):
            frappe.delete_doc('Property Setter', name)
    frappe.clear_cache()
