"""Mark historical BOQs as per-unit without repricing submitted records."""
import frappe


def execute():
    for slug in ('material_costs', 'labor_costs', 'contractors_table', 'expenses_table', 'boq'):
        frappe.reload_doc('contractor_app', 'doctype', slug, force=True)
    # Equipment may be supplied by a site's existing BOQ customization.
    meta = frappe.get_meta('BOQ')
    equipment = meta.get_field('custom_equipment')
    if equipment and equipment.options:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
        child = frappe.get_meta(equipment.options)
        if child.istable and not child.has_field('per_unit_qty'):
            create_custom_fields({equipment.options: [{
                'fieldname': 'per_unit_qty', 'fieldtype': 'Float', 'label': 'Quantity per Clause Unit',
                'default': '1', 'precision': '6', 'in_list_view': 1, 'insert_after': 'item',
                'module': 'Contractor App',
            }]}, update=True)
        if not meta.has_field('custom_total_equipment_costs'):
            create_custom_fields({'BOQ': [{
                'fieldname': 'custom_total_equipment_costs', 'fieldtype': 'Currency',
                'label': 'Total Equipment Costs', 'read_only': 1, 'insert_after': 'total_expenses',
                'module': 'Contractor App',
            }]}, update=True)
    for row in frappe.get_all('BOQ', or_filters=[['quantity_basis', '=', ''], ['quantity_basis', 'is', 'not set']],
            fields=['name', 'total_cost', 'project_qty']):
        cost = float(row.total_cost or 0)
        qty = float(row.project_qty or 0)
        frappe.db.set_value('BOQ', row.name, {'quantity_basis': 'Per Unit',
            'unit_cost': cost, 'project_total_cost': cost * qty}, update_modified=False)
    frappe.clear_cache(doctype='BOQ')
