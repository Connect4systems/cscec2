const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const handlers = {};
const calls = [];
const routes = [];
const context = vm.createContext({
    contractor: {fetch_project_name() {}}, __: text => text,
    frappe: {provide() {}, ui: {form: {on(type, events) { handlers[type] = events; }}},
        model: {can_create: () => true, sync: doc => [doc]},
        async call(args) { calls.push(args); return {message: {doc: {name: 'new-budget'}}}; },
        set_route(...args) { routes.push(args); }}
});
const source = fs.readFileSync(path.join(__dirname, '../contractor/public/js/doctype/project_commercial.js'), 'utf8').replace(/^\{%.*?%\}\r?\n/gm, '');
vm.runInContext(source, context);
(async () => {
    for (const type of ['Project Contract','Project Offer']) {
        for (const status of [0,1,2]) {
            const buttons = [];
            const frm = {doctype: type, doc: {name: 'PC-1', docstatus: status, created_project: 'PROJ-1'},
                fields_dict: {clauses: {grid: {}}}, trigger() {}, is_dirty: () => false,
                add_custom_button(label, callback, group) { buttons.push({label, callback, group}); }};
            handlers[type].refresh(frm);
            const budget = buttons.filter(button => button.label === 'Project Budget');
            assert.strictEqual(budget.length, type === 'Project Contract' && status === 1 ? 1 : 0);
            if (budget.length) {
                assert.strictEqual(budget[0].group, 'Create');
                await budget[0].callback();
                assert.strictEqual(calls[0].method, 'contractor.project_budget.create_budget');
                assert.strictEqual(calls[0].args.project_contract, 'PC-1');
                assert.strictEqual(routes[0].join('/'), 'Form/Project Budget/new-budget');
            }
        }
    }
    console.log('Project Contract budget action gating and routing checks passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
