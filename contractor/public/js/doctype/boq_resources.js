frappe.provide('contractor');
if (!contractor.boq_resource_handlers_loaded) {
contractor.boq_resource_handlers_loaded = true;
const resource_totals = {material_costs: 'total_material_costs', labor_costs: 'total_labor_costs',
    contractors_table: 'total_contractors', expenses_table: 'total_expenses', custom_equipment: 'custom_total_equipment_costs'};
const registered = new Set();
contractor.recalculate_boq_resources = function (frm) {
    if (!['BOQ', 'Template BOQ'].includes(frm.doctype) || frm.doc.docstatus) return;
    const project_basis = frm.doctype === 'BOQ' && frm.doc.quantity_basis === 'Project Quantity';
    const project_qty = flt(frm.doc.project_qty);
    let total = 0;
    for (const [table, total_field] of Object.entries(resource_totals)) {
        let subtotal = 0;
        for (const row of frm.doc[table] || []) {
            if (project_basis) row.qty = flt(row.per_unit_qty) * project_qty;
            row.total_cost = flt(row.qty) * flt(row.cost);
            subtotal += row.total_cost;
        }
        if (frm.fields_dict[total_field]) {
            frm.doc[total_field] = subtotal;
            frm.refresh_field(total_field);
        }
        if (frm.fields_dict[table]) frm.refresh_field(table);
        total += subtotal;
    }
    if (frm.doctype === 'BOQ') {
        frm.doc.total_cost = total;
        frm.doc.unit_cost = project_basis ? (project_qty > 0 ? total / project_qty : 0) : total;
        frm.doc.project_total_cost = project_basis ? total : total * project_qty;
        for (const field of ['total_cost', 'unit_cost', 'project_total_cost']) frm.refresh_field(field);
    }
};
const recalculate = frm => contractor.recalculate_boq_resources(frm);
function resource_added(frm, cdt, cdn) {
    if (!['BOQ', 'Template BOQ'].includes(frm.doctype)) return;
    const row = locals[cdt][cdn];
    row.per_unit_qty = 1;
    row.qty = 1;
    row.cost = 0;
    if (cdt === 'Material costs') row.depreciasion_percentage = 0;
    recalculate(frm);
}
function register(doctype) {
    if (!doctype || registered.has(doctype)) return;
    registered.add(doctype);
    const handlers = {qty: recalculate, per_unit_qty: recalculate, cost: recalculate,
        async item(frm, cdt, cdn) {
            if (!['BOQ', 'Template BOQ'].includes(frm.doctype)) return;
            const row = locals[cdt][cdn];
            const item = row.item;
            if (!item) return;
            const result = await frappe.db.get_value('Item', item, 'stock_uom');
            if (row.item === item && result.message) await frappe.model.set_value(cdt, cdn, 'uom', result.message.stock_uom);
        }};
    for (const table of Object.keys(resource_totals)) handlers[table + '_add'] = resource_added;
    frappe.ui.form.on(doctype, handlers);
}
for (const type of ['Material costs', 'Labor costs', 'Contractors table', 'Expenses Table']) register(type);
contractor.setup_boq_resources = function (frm) {
    if (!['BOQ', 'Template BOQ'].includes(frm.doctype)) return;
    const project_basis = frm.doctype === 'BOQ' && frm.doc.quantity_basis === 'Project Quantity';
    for (const table of Object.keys(resource_totals)) {
        if (!frm.fields_dict[table]) continue;
        const control = frm.fields_dict[table];
        register(control.df.options);
        control.grid.update_docfield_property('qty', 'read_only', project_basis ? 1 : 0);
        control.grid.update_docfield_property('qty', 'label', project_basis ? __('Project Quantity') : __('Quantity per Clause Unit'));
        if ((control.grid.docfields || []).some(field => field.fieldname === 'per_unit_qty')) {
            control.grid.update_docfield_property('per_unit_qty', 'hidden', project_basis ? 0 : 1);
        }
    }
    if (frm.doctype === 'BOQ') frm.set_df_property('total_cost', 'label',
        project_basis ? __('Total Project Cost') : __('Historical BOQ Unit Cost'));
};
}
