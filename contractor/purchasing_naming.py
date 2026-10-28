"""Project-based purchasing identifiers, without changing native transaction behavior."""
import frappe
from frappe.model.naming import make_autoname


def project_name(doc, prefix):
    if not doc.get('project'):
        frappe.throw(f'Select Project before saving {doc.doctype}')
    abbreviation = str(frappe.db.get_value('Project', doc.project, 'custom_abbreviation') or '').strip()
    if not abbreviation:
        frappe.throw('Enter Project Abbreviation on the selected Project before saving')
    return make_autoname(f'{prefix}-{abbreviation}-.####')
