const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const forms = {};
const context = vm.createContext({
    contractor: {}, flt: value => Number(value || 0), __: text => text,
    frappe: {provide() {}, ui: {form: {on(type, handlers) { forms[type] = handlers; }}}}
});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../contractor/public/js/doctype/boq_resources.js'), 'utf8'), context);
function form(type, status=0) {
    const fields = {};
    for (const [table, child] of [['material_costs','Material costs'],['labor_costs','Labor costs'],
        ['contractors_table','Contractors table'],['expenses_table','Expenses Table'],['equipment_costs','BOQ Equipment Cost']]) {
        fields[table] = {df: {options: child}, grid: {docfields: [{fieldname: 'per_unit_qty'}],
            changes: {}, update_docfield_property(field, property, value) { this.changes[field + ':' + property] = value; }}};
    }
    for (const field of ['total_material_costs','total_labor_costs','total_contractors','total_expenses','total_equipment_costs']) fields[field] = {};
    return {doctype: type, doc: {docstatus: status, quantity_basis: 'Project Quantity', project_qty: 100,
        material_costs: [{qty: 2, per_unit_qty: 2, cost: 5}], labor_costs: [], contractors_table: [], expenses_table: []},
        fields_dict: fields, visible: {}, refresh_field() {}, set_df_property() {},
        toggle_display(name, show) { this.visible[name] = show; }};
}
const boq = form('BOQ');
context.contractor.setup_boq_resources(boq);
context.contractor.recalculate_boq_resources(boq);
assert.strictEqual(boq.doc.material_costs[0].qty, 200);
assert.strictEqual(boq.doc.total_cost, 1000);
assert.strictEqual(boq.doc.unit_cost, 10);
context.contractor.recalculate_boq_resources(boq);
assert.strictEqual(boq.doc.material_costs[0].qty, 200);
boq.doc.project_qty = 150;
context.contractor.recalculate_boq_resources(boq);
assert.strictEqual(boq.doc.total_cost, 1500);
assert.strictEqual(boq.fields_dict.material_costs.grid.changes['qty:read_only'], 1);
const template = form('Template BOQ');
context.contractor.setup_boq_resources(template);
context.contractor.recalculate_boq_resources(template);
assert.strictEqual(template.doc.material_costs[0].qty, 2);
assert.strictEqual(template.doc.material_costs[0].total_cost, 10);
assert.strictEqual(template.fields_dict.material_costs.grid.changes['qty:read_only'], 0);
assert.strictEqual(template.fields_dict.material_costs.grid.changes['per_unit_qty:hidden'], 1);
const historical = form('BOQ', 1);
historical.doc.quantity_basis = 'Per Unit';
historical.doc.total_cost = 10;
context.contractor.recalculate_boq_resources(historical);
assert.strictEqual(historical.doc.material_costs[0].qty, 2);
assert.strictEqual(historical.doc.total_cost, 10);
const equipment = form('BOQ');
equipment.doc.equipment_costs = [{per_unit_qty: 0.25, qty: 0, cost: 40}];
context.contractor.setup_boq_resources(equipment);
context.contractor.recalculate_boq_resources(equipment);
assert.strictEqual(equipment.doc.equipment_costs[0].qty, 25);
assert.strictEqual(equipment.doc.total_equipment_costs, 1000);
assert.strictEqual(equipment.doc.total_cost, 2000);
assert.strictEqual(equipment.visible.equipment_costs, true);
assert(forms['BOQ Equipment Cost']);
const existing = form('BOQ');
existing.doc.custom_equipment = [{per_unit_qty: 1, qty: 0, cost: 10}];
existing.fields_dict.custom_equipment = existing.fields_dict.equipment_costs;
context.contractor.setup_boq_resources(existing);
context.contractor.recalculate_boq_resources(existing);
assert.strictEqual(existing.visible.equipment_costs, false);
assert.strictEqual(existing.visible.custom_equipment, true);
assert.strictEqual(existing.doc.total_equipment_costs, 1000);
console.log('BOQ project quantities, equipment visibility and template checks passed');
