const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
let dialog;
const rows = [
    {name: 'group', is_group: 1, series_number: '4', clause_title: 'Civil'},
    {name: 'detail', is_group: 0, series_number: '4_2', parent_series: '4', clause_title: 'Concrete', qty: 10}
];
function wrapper() {
    return {content: '', html(value) { this.content = value; }, text(value) { this.content = value; },
        find() { return {on() {}}; }, prop() {}};
}
class Dialog {
    constructor(options) {
        dialog = this;
        this.options = options;
        this.fields_dict = {};
        this.values = {};
        this.visible = {};
        for (const field of options.fields) {
            const control = {$input: wrapper(), $wrapper: wrapper(), df: field};
            control.toggle = show => {
                control.df.hidden = show ? 0 : 1;
                this.visible[field.fieldname] = !!show;
            };
            this.fields_dict[field.fieldname] = control;
            this.values[field.fieldname] = field.default || '';
        }
    }
    get_value(name) { return this.values[name]; }
    show() {}
    change(name, value) {
        this.values[name] = value;
        this.options.fields.find(field => field.fieldname === name).onchange();
    }
}
const context = vm.createContext({
    console, __: text => text,
    frappe: {ui: {form: {on() {}}, Dialog},
        call: async () => ({message: {project: 'PROJ-1', clauses: rows}}),
        utils: {escape_html: text => text}, msgprint() {}}
});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../contractor/contractor_app/doctype/cr/cr.js'), 'utf8'), context);
(async () => {
    await context.open_cr_project_clause_picker({doc: {name: 'CR-1'}}, () => true);
    assert.strictEqual(dialog.visible.clause_group, false);
    assert.strictEqual(dialog.visible.select_all, false);
    assert.strictEqual(dialog.visible.details, false);
    dialog.change('fetch_all', 0);
    assert.strictEqual(dialog.visible.clause_group, true);
    assert.strictEqual(dialog.visible.select_all, true);
    assert.strictEqual(dialog.visible.details, false);
    dialog.change('clause_group', '4 - Civil');
    assert.strictEqual(dialog.visible.details, true);
    const html = dialog.fields_dict.details.$wrapper.content;
    assert(html.includes('<table'));
    assert(html.includes('Concrete'));
    assert(html.includes('cr-detail-choice'));
    assert(html.includes('cr-detail-qty'));
    assert(html.includes('value="10"'));
    assert.strictEqual(typeof dialog.toggle_display, 'undefined');
    dialog.change('select_all', 1);
    assert.strictEqual(dialog.visible.details, false);
    dialog.change('select_all', 0);
    assert.strictEqual(dialog.visible.details, true);
    dialog.change('fetch_all', 1);
    assert.strictEqual(dialog.visible.clause_group, false);
    assert.strictEqual(dialog.visible.select_all, false);
    assert.strictEqual(dialog.visible.details, false);
    console.log('CR picker visibility checks passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
