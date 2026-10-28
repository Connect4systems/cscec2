const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const handlers = {};
const calls = [];
let responders = [];
const context = vm.createContext({
    contractor: {}, flt: value => Number(value || 0),
    frappe: {
        provide() {}, ui: {form: {on(type, events) { handlers[type] = events; }}},
        utils: {debounce: fn => fn},
        call(args) { calls.push(args); return new Promise(resolve => responders.push(resolve)); }
    }
});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../contractor/public/js/doctype/subcontract_commercial.js'), 'utf8'), context);
const tick = () => new Promise(resolve => setImmediate(resolve));
function result(total) {
    return {message: {totals: {grand_total: total, total_deductions: total * 0.05, net_payable: total * 0.95},
        clauses: [{amount: 200}], taxes: [{name: 'server-tax-id', tax_amount: total - 200}], deductions: [{value: total * 0.05}]}};
}
(async () => {
    assert(handlers.CR);
    assert(handlers['Subcontractor Contract']);
    const clause = {name: 'local-clause', clause_title: 'Concrete', qty: 2, rate: 100};
    const tax = {name: 'local-tax', charge_type: 'On Net Total', account_head: 'VAT'};
    const deduction = {name: 'local-deduction', title: 'Edited retention', account: 'Retention', percent: 5};
    const frm = {doctype: 'Subcontractor Contract', doc: {project: 'P1', docstatus: 0,
        clauses: [clause], taxes: [tax], deductions: [deduction]},
        fields_dict: {grand_total: {}, total_deductions: {}, net_payable: {}}, refresh_fields() {}};
    handlers['Subcontractor Contract'].calculate_subcontract_totals(frm);
    assert.strictEqual(calls[0].method, 'contractor.subcontract_commercial.preview');
    responders.shift()(result(220));
    await tick();
    assert.strictEqual(frm.doc.net_payable, 209);
    assert.strictEqual(clause.amount, 200);
    assert.strictEqual(tax.name, 'local-tax');
    assert.strictEqual(deduction.title, 'Edited retention');
    assert.strictEqual(deduction.value, 11);
    handlers['Subcontractor Contract'].calculate_subcontract_totals(frm);
    handlers['Subcontractor Contract'].calculate_subcontract_totals(frm);
    responders[1](result(240));
    await tick();
    responders[0](result(230));
    await tick();
    assert.strictEqual(frm.doc.grand_total, 240); // stale result must not replace current edits
    responders = [];
    const count = calls.length;
    frm.doc.docstatus = 1;
    handlers['Subcontractor Contract'].calculate_subcontract_totals(frm);
    assert.strictEqual(calls.length, count);
    frm.doc.docstatus = 0;
    frm.doc.clauses[0].qty = 0;
    handlers['Subcontractor Contract'].calculate_subcontract_totals(frm);
    assert.strictEqual(calls.length, count);
    console.log('Subcontract commercial preview and stale-response checks passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
