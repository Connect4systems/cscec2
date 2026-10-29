const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const forms = {};
const schema = JSON.parse(fs.readFileSync(path.join(__dirname,
    '../contractor/contractor_app/doctype/costing_note_items/costing_note_items.json'), 'utf8'));
const context = vm.createContext({
    contractor: {fetch_project_name() {}},
    frappe: {ui: {form: {on(type, handlers) { forms[type] = handlers; }}}}
});
const source = fs.readFileSync(path.join(__dirname,
    '../contractor/contractor_app/doctype/costing_note/costing_note.js'), 'utf8');
vm.runInContext(source.replace(/\{%[\s\S]*?%\}/g, ''), context);
for (const tender of [true, false]) {
    const changes = {};
    const frm = {
        doc: {tender_analysis: tender ? 'TA-1' : null},
        is_new() { return true; },
        set_query(field, table) {
            if (table === 'costing_note_items') {
                assert(schema.fields.some(df => df.fieldname === field), `Missing query field ${field}`);
            }
        },
        fields_dict: {costing_note_items: {grid: {
            docfields: schema.fields,
            update_docfield_property(field, property, value) {
                assert(schema.fields.some(df => df.fieldname === field), `Missing grid field ${field}`);
                changes[field + ':' + property] = value;
            }
        }}}
    };
    forms['Costing Note'].setup(frm);
    forms['Costing Note'].refresh(frm);
    assert.strictEqual(changes['contractual_clause:hidden'], !tender);
    assert.strictEqual(changes['clause_title:hidden'], !tender);
}
console.log('Costing Note setup and refresh work without removed Item fields');
