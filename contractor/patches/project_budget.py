"""Install budget metadata without resaving contracts or changing pricing."""
import frappe
from frappe.utils import now


def execute():
    for slug in ('project_budget_clause', 'project_budget', 'project_contract'):
        frappe.reload_doc('contractor_app', 'doctype', slug, force=True)
        doctype = slug.replace('_', ' ').title()
        frappe.db.set_value('DocType', doctype, 'modified', now(), update_modified=False)
        frappe.clear_cache(doctype=doctype)
    frappe.reload_doc('contractor_app', 'workspace', 'tender', force=True)
