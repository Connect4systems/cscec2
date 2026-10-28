"""Keep purchasing naming independent of the former Order Type customization."""
import frappe


def execute():
    record = frappe.db.get_value('Custom Field',
        {'dt': 'Purchase Order', 'fieldname': 'custom_type'}, ['name', 'module'], as_dict=True)
    if record and (not record.module or record.module == 'Contractor App'):
        frappe.delete_doc('Custom Field', record.name)
    frappe.clear_cache(doctype='Purchase Order')
    frappe.clear_cache(doctype='Purchase Receipt')
