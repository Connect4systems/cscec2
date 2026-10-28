"""Apply purchasing commercial tabs without recalculating historical documents."""
import json
from pathlib import Path

import frappe
from frappe.utils import now


def execute():
    root = Path(__file__).parents[1] / 'contractor_app' / 'doctype'
    for slug in ('cr_clause', 'subcontractor_contract_clause', 'cr', 'subcontractor_contract', 'subcontract_clearnce'):
        frappe.reload_doc('contractor_app', 'doctype', slug, force=True)
        schema = json.loads((root / slug / (slug + '.json')).read_text(encoding='utf-8'))
        if slug in ('cr', 'subcontractor_contract', 'subcontract_clearnce'):
            for setter in frappe.get_all('Property Setter', filters={
                    'doc_type': schema['name'], 'property': 'field_order'}, fields=['name', 'value']):
                try:
                    old = json.loads(setter.value)
                except (TypeError, ValueError):
                    continue
                if not isinstance(old, list):
                    continue
                order = list(schema['field_order'])
                # Keep site-owned fields while applying the requested standard tabs.
                extras = [name for name in old if name not in order and name != 'clauses_section']
                position = order.index('connections_tab')
                order[position:position] = extras
                frappe.db.set_value('Property Setter', setter.name, 'value', json.dumps(order))
        frappe.db.set_value('DocType', schema['name'], 'modified', now(), update_modified=False)
    frappe.clear_cache()
