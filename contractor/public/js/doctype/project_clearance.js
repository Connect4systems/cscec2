frappe.provide('contractor');
if (!contractor.clearance_handlers_loaded) {
contractor.clearance_handlers_loaded = true;
const types = ['Project Clearnce', 'Subcontract Clearnce'];
const calculate = frm => { if (types.includes(frm.doctype) && !frm.doc.legacy_record) frm.trigger('calculate_clearance'); };
const handlers = {
    refresh(frm) {
        if (frm.doc.legacy_record) {
            if (frm.doc.docstatus === 1) frm.add_custom_button(__('Create Invoice'), async () => {
                const path = frm.doctype === 'Project Clearnce' ? 'clearence.clearence.make_sales_invoice' : 'purchase_clearence.purchase_clearence.make_purchase_invoice';
                const r = await frappe.call({method: 'contractor.contractor_app.doctype.' + path, args: {clearence: frm.doc.name}});
                const docs = frappe.model.sync(r.message);
                frappe.set_route('Form', docs[0].doctype, docs[0].name);
            });
            return;
        }
        frm.fields_dict.clauses.grid.cannot_add_rows = true;
        frm.fields_dict.clauses.grid.update_docfield_property('rate', 'read_only', frm.doctype === 'Project Clearnce' || !!frm.doc.subcontractor_contract);
        if (frm.doc.subcontractor_contract) {
            frm.set_df_property('project', 'read_only', 1);
            frm.set_df_property('supplier', 'read_only', 1);
        }
        if (frm.doc.invoice) frm.add_custom_button(__('Open Invoice'), () => frappe.set_route('Form', frm.doc.invoice_doctype, frm.doc.invoice));
        if (frm.doc.deduction_entry) frm.add_custom_button(__('Deduction Entry'), () => frappe.set_route('Form', 'Journal Entry', frm.doc.deduction_entry));
        if (frm.doc.docstatus === 0) calculate(frm);
    },
    setup(frm) {
        frm.set_query('project', () => ({filters: {project_contract: ['is', 'set'], status: ['!=', 'Cancelled']}}));
        frm.set_query('taxes_and_charges', () => ({filters: {company: frm.doc.company, disabled: 0}}));
        for (const [field, table] of [['account', 'deductions'], ['account_head', 'taxes']]) {
            frm.set_query(field, table, () => ({filters: {company: frm.doc.company, is_group: 0}}));
        }
        frm.set_query('cost_center', () => ({filters: {company: frm.doc.company, is_group: 0}}));
    },
    async project(frm) {
        if (!frm.doc.project || frm.doc.legacy_record || frm.doc.docstatus || frm.doc.subcontractor_contract) return;
        const name = frm.doc.project;
        const r = await frappe.call({method: 'contractor.project_clearances.create_clearance',
            args: {project: name, doctype: frm.doctype, supplier: frm.doc.supplier || null}});
        if (frm.doc.project !== name) return;
        for (const key of ['project_contract', 'project_offer', 'tender_analysis', 'title', 'company', 'currency', 'conversion_rate', 'customer', 'taxes_and_charges', 'selling_deductions_template', 'delivery_date']) {
            if (frm.fields_dict[key]) frm.doc[key] = r.message[key];
        }
        for (const table of ['clauses', 'taxes', 'deductions']) {
            frm.clear_table(table);
            for (const row of r.message[table] || []) {
                const values = {...row};
                for (const key of ['name', 'doctype', 'parent', 'parentfield', 'parenttype', 'idx', 'owner', 'creation', 'modified', 'modified_by', '__islocal', '__unsaved']) delete values[key];
                frm.add_child(table, values);
            }
        }
        frm.refresh_fields(); frm.dirty(); calculate(frm);
    },
    calculate_clearance(frm) {
        frm._certificate_revision = (frm._certificate_revision || 0)+1;
        if (!frm._calculate_certificate) frm._calculate_certificate = frappe.utils.debounce(async () => {
            if (frm.doc.docstatus || frm.doc.legacy_record || !frm.doc.project || !(frm.doc.clauses || []).length) return;
            if (frm.doctype === 'Subcontract Clearnce' && !frm.doc.supplier) return;
            if ((frm.doc.taxes || []).some(row => !row.account_head || !row.charge_type)) return;
            if ((frm.doc.deductions || []).some(row => !row.account)) return;
            const revision = frm._certificate_revision;
            const r = await frappe.call({method: 'contractor.project_clearances.preview', args: {doc: JSON.stringify(frm.doc)}});
            if (!r.message || revision !== frm._certificate_revision || frm.doc.docstatus) return;
            for (const field of ['clauses', 'taxes', 'deductions']) {
                (frm.doc[field] || []).forEach((row, i) => {
                    const values = {...r.message[field][i]};
                    for (const key of ['name', 'parent', 'parentfield', 'parenttype', 'doctype']) delete values[key];
                    Object.assign(row, values);
                });
            }
            for (const [field, value] of Object.entries(r.message)) {
                if (frm.fields_dict[field] && !['Table', 'Tab Break', 'Section Break', 'Column Break'].includes(frm.fields_dict[field].df.fieldtype)) frm.doc[field] = value;
            }
            frm.refresh_fields();
        }, 400);
        frm._calculate_certificate();
    },
    before_save(frm) { frm._certificate_revision = (frm._certificate_revision || 0)+1; },
    async taxes_and_charges(frm) {
        if (!frm.doc.taxes_and_charges || frm.doc.legacy_record) return;
        const template = frm.doc.taxes_and_charges;
        const r = await frappe.call({method: 'contractor.project_contract_taxes.get_tax_template',
            args: {template, company: frm.doc.company, buying: frm.doctype === 'Subcontract Clearnce' ? 1 : 0}});
        if (template !== frm.doc.taxes_and_charges) return;
        frm.clear_table('taxes');
        for (const row of r.message || []) frm.add_child('taxes', row);
        frm.refresh_field('taxes');frm.dirty();calculate(frm);
    },
    async load_deductions(frm) {
        const buying = frm.doctype === 'Subcontract Clearnce';
        const template = frm.doc[buying ? 'purchasing_deductions_template' : 'selling_deductions_template'];
        if (!template || frm.doc.legacy_record) return;
        const r = await frappe.call({method: 'contractor.project_clearances.deduction_template', args: {template, company: frm.doc.company, buying: buying ? 1 : 0}});
        frm.clear_table('deductions');
        for (const row of r.message || []) frm.add_child('deductions', row);
        frm.refresh_field('deductions');frm.dirty();calculate(frm);
    },
    selling_deductions_template(frm) {frm.trigger('load_deductions');},
    purchasing_deductions_template(frm) {frm.trigger('load_deductions');},
    supplier: calculate, discount_amount: calculate, additional_discount_percentage: calculate,
    apply_discount_on: calculate, conversion_rate: calculate, disable_rounded_total: calculate
};
for (const doctype of types) frappe.ui.form.on(doctype, handlers);
frappe.ui.form.on('Clearnce Clause', {qty: calculate, rate: calculate, clauses_remove: calculate,
    qty_percentage(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, 'qty', Math.max(0, flt(row.total_required_qty)-flt(row.project_previous_qty))*flt(row.qty_percentage)/100);
    }
});
frappe.ui.form.on('Deduction', {percent: calculate, account: calculate, deductions_remove: calculate});
for (const doctype of ['Sales Taxes and Charges', 'Purchase Taxes and Charges']) {
    frappe.ui.form.on(doctype, {rate: calculate, tax_amount: calculate, charge_type: calculate,
        async account_head(frm, cdt, cdn) {
            if (!types.includes(frm.doctype) || frm.doc.legacy_record) return;
            const row = locals[cdt][cdn];
            const account = row.account_head;
            if (!account) return;
            const r = await frappe.db.get_value('Account', account, 'account_name');
            if (row.account_head !== account) return;
            if (!row.description) await frappe.model.set_value(cdt, cdn, 'description', r.message.account_name || account);
            calculate(frm);
        },
        row_id: calculate, included_in_print_rate: calculate, add_deduct_tax: calculate, taxes_remove: calculate});
}
}
