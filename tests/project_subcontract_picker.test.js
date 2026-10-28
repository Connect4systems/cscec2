const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
let project_handlers;
let dialog;
const calls = [];
const routes = [];
const context = vm.createContext({
    __: text => text,
    frappe: {
        ui: {form: {on(type, handlers) { if (type === 'Project') project_handlers = handlers; }},
            Dialog: class {
                constructor(options) { this.options = options; this.values = {}; dialog = this; }
                get_value(name) { return this.values[name]; }
                set_value(name, value) { this.values[name] = value; }
                show() {}
                hide() {}
            }},
        async call(args) {
            calls.push(args);
            if (args.method.endsWith('project_contract_options')) return {message: {
                suppliers: [{name: 'S1'}, {name: 'S2'}],
                contracts: [{name: 'C1', supplier: 'S1'}, {name: 'C2', supplier: 'S2'}]}};
            return {message: {name: 'new-certificate'}};
        },
        model: {sync: doc => [doc]}, set_route(...args) { routes.push(args); }
    }
});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../contractor/public/js/doctype/project.js'), 'utf8'), context);
(async () => {
    for (const project_contract of [null, 'PC-1']) {
        const buttons = [];
        project_handlers.refresh({doc: {name: 'P1', project_contract}, meta: {fields: []},
            is_new: () => false, set_query() {}, set_df_property() {},
            add_custom_button(label) { buttons.push(label); }});
        assert.strictEqual(buttons.filter(label => label === 'Subcontract Clearnce').length, 1);
    }
    const frm = {doc: {name: 'P1'}, is_new: () => false, is_dirty: () => false};
    await project_handlers.create_subcontract_clearance(frm);
    const supplier = dialog.options.fields.find(field => field.fieldname === 'supplier');
    const contract = dialog.options.fields.find(field => field.fieldname === 'subcontractor_contract');
    assert.strictEqual(supplier.get_query().filters.name[1].join(','), 'S1,S2');
    dialog.values.supplier = 'S1';
    dialog.values.subcontractor_contract = 'C2';
    supplier.onchange();
    assert.strictEqual(dialog.values.subcontractor_contract, null);
    const filters = contract.get_query().filters;
    assert.strictEqual(filters.project, 'P1');
    assert.strictEqual(filters.docstatus, 1);
    assert.strictEqual(filters.supplier, 'S1');
    assert.strictEqual(filters.name[1].join(','), 'C1');
    await dialog.options.primary_action({supplier: 'S1', subcontractor_contract: 'C1'});
    const args = calls[calls.length - 1].args;
    assert.strictEqual(args.project, 'P1');
    assert.strictEqual(args.supplier, 'S1');
    assert.strictEqual(args.subcontractor_contract, 'C1');
    assert.strictEqual(routes[0].join('/'), 'Form/Subcontract Clearnce/new-certificate');
    console.log('Project supplier and contract selection checks passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
