"""Expose equipment resources while retaining existing site-specific equipment rows."""
import frappe
from frappe.utils import now


def execute():
    for slug in ('boq_equipment_cost', 'boq', 'template_boq'):
        frappe.reload_doc('contractor_app', 'doctype', slug, force=True)
    meta = frappe.get_meta('BOQ')
    legacy = meta.get_field('custom_equipment')
    saved_totals = {}
    if meta.has_field('custom_total_equipment_costs'):
        for row in frappe.get_all('BOQ', fields=['name', 'custom_total_equipment_costs']):
            if row.custom_total_equipment_costs:
                saved_totals[row.name] = float(row.custom_total_equipment_costs)
    if legacy:
        custom_field = frappe.db.get_value('Custom Field',
            {'dt': 'BOQ', 'fieldname': 'custom_equipment'}, 'name')
        if custom_field:
            frappe.db.set_value('Custom Field', custom_field,
                {'insert_after': 'equipment_costs', 'hidden': 0})
        child = frappe.get_meta(legacy.options)
        if child.istable and not child.has_field('per_unit_qty'):
            from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
            create_custom_fields({legacy.options: [{
                'fieldname': 'per_unit_qty', 'fieldtype': 'Float', 'label': 'Quantity per Clause Unit',
                'default': '1', 'precision': '6', 'insert_after': 'item', 'in_list_view': 1,
                'module': 'Contractor App',
            }]}, update=True)
        # Fill the newly visible subtotal without resaving or repricing old BOQs.
        if child.has_field('qty') and child.has_field('cost'):
            totals = {}
            for row in frappe.get_all(legacy.options, filters={'parenttype': 'BOQ', 'parentfield': 'custom_equipment'},
                    fields=['parent', 'qty', 'cost']):
                totals[row.parent] = totals.get(row.parent, 0) + float(row.qty or 0) * float(row.cost or 0)
            for parent, total in totals.items():
                saved_totals.setdefault(parent, total)
    for parent, total in saved_totals.items():
        # New standard equipment rows are not copied from old tables.
        if not frappe.db.exists('BOQ Equipment Cost', {'parent': parent, 'parenttype': 'BOQ'}):
            frappe.db.set_value('BOQ', parent, 'total_equipment_costs', total, update_modified=False)
    total_field = frappe.db.get_value('Custom Field',
        {'dt': 'BOQ', 'fieldname': 'custom_total_equipment_costs'}, 'name')
    if total_field:
        frappe.db.set_value('Custom Field', total_field, {'hidden': 1, 'read_only': 1})
    # Retain every site-owned field in customized ordering and insert the Equipment tab.
    for doctype in ('BOQ', 'Template BOQ'):
        for setter in frappe.get_all('Property Setter', filters={'doc_type': doctype,
                'property': 'field_order'}, fields=['name', 'value']):
            import json
            try:
                order = json.loads(setter.value)
            except (TypeError, ValueError):
                continue
            if not isinstance(order, list):
                continue
            equipment_fields = ['equipment_tab' if doctype == 'BOQ' else 'equipment_section',
                'equipment_costs', 'total_equipment_costs']
            if doctype == 'BOQ' and legacy:
                equipment_fields.insert(2, 'custom_equipment')
            order = [field for field in order if field not in equipment_fields]
            position = order.index('expenses_tab') if 'expenses_tab' in order else len(order)
            order[position:position] = equipment_fields
            frappe.db.set_value('Property Setter', setter.name, 'value', json.dumps(order))
        frappe.db.set_value('DocType', doctype, 'modified', now(), update_modified=False)
        frappe.clear_cache(doctype=doctype)
