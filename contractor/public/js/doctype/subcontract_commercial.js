frappe.provide('contractor');
if (!contractor.subcontract_commercial_loaded) {
contractor.subcontract_commercial_loaded = true;
const commercial_types = ['CR', 'Subcontractor Contract'];
const recalculate = frm => {
    if (commercial_types.includes(frm.doctype) && !frm.doc.docstatus) frm.trigger('calculate_subcontract_totals');
};
const handlers = {
    setup(frm) {
        frm.set_query('taxes_and_charges', () => ({filters: {company: frm.doc.company, disabled: 0}}));
        for (const [field, table] of [['account_head', 'taxes'], ['account', 'deductions']]) {
            frm.set_query(field, table, () => ({filters: {company: frm.doc.company, is_group: 0}}));
        }
    },
    refresh: recalculate,
    before_save(frm) { frm._commercial_revision = (frm._commercial_revision || 0) + 1; },
    async company(frm) {
        frm._commercial_revision = (frm._commercial_revision || 0) + 1;
        if (!frm.doc.company || frm.doc.docstatus) return;
        const company = frm.doc.company;
        const currency = await frappe.db.get_value('Company', company, 'default_currency');
        if (frm.doc.company !== company) return;
        if (!frm.doc.currency && currency.message) await frm.set_value('currency', currency.message.default_currency);
        if (!frm.doc.taxes_and_charges && !(frm.doc.taxes || []).length) {
            const template = await frappe.db.get_value('Purchase Taxes and Charges Template',
                {company, disabled: 0, is_default: 1}, 'name');
            if (frm.doc.company === company && !frm.doc.taxes_and_charges && !(frm.doc.taxes || []).length && template.message && template.message.name) {
                await frm.set_value('taxes_and_charges', template.message.name);
            }
        }
        recalculate(frm);
    },
    async taxes_and_charges(frm) {
        frm._commercial_revision = (frm._commercial_revision || 0) + 1;
        if (frm.doc.docstatus) return;
        const template = frm.doc.taxes_and_charges;
        const company = frm.doc.company;
        if (!template) { frm.clear_table('taxes'); frm.refresh_field('taxes'); return recalculate(frm); }
        const r = await frappe.call({method: 'contractor.project_contract_taxes.get_tax_template',
            args: {template, company, buying: 1}});
        if (frm.doc.taxes_and_charges !== template || frm.doc.company !== company || frm.doc.docstatus) return;
        frm.clear_table('taxes');
        for (const row of r.message || []) frm.add_child('taxes', row);
        frm.refresh_field('taxes'); frm.dirty(); recalculate(frm);
    },
    async purchasing_deductions_template(frm) {
        frm._commercial_revision = (frm._commercial_revision || 0) + 1;
        if (frm.doc.docstatus) return;
        const template = frm.doc.purchasing_deductions_template;
        const company = frm.doc.company;
        if (!template) return;
        const r = await frappe.call({method: 'contractor.project_clearances.deduction_template',
            args: {template, company, buying: 1}});
        if (frm.doc.purchasing_deductions_template !== template || frm.doc.company !== company || frm.doc.docstatus) return;
        frm.clear_table('deductions');
        for (const row of r.message || []) frm.add_child('deductions', row);
        frm.refresh_field('deductions'); frm.dirty(); recalculate(frm);
    },
    calculate_subcontract_totals(frm) {
        frm._commercial_revision = (frm._commercial_revision || 0) + 1;
        if (!frm._calculate_subcontract_totals) frm._calculate_subcontract_totals = frappe.utils.debounce(async () => {
            if (frm.doc.docstatus || !frm.doc.project) return;
            if ((frm.doc.clauses || []).some(row => !row.is_group && (!row.clause_title || flt(row.qty) <= 0))) return;
            if ((frm.doc.taxes || []).some(row => !row.account_head || !row.charge_type)) return;
            if ((frm.doc.deductions || []).some(row => !row.account)) return;
            const revision = frm._commercial_revision;
            const result = await frappe.call({method: 'contractor.subcontract_commercial.preview', args: {doc: JSON.stringify(frm.doc)}});
            if (!result.message || revision !== frm._commercial_revision || frm.doc.docstatus) return;
            const values = result.message;
            for (const [field, value] of Object.entries(values.totals)) {
                if (frm.fields_dict[field]) frm.doc[field] = value;
            }
            for (const table of ['clauses', 'taxes', 'deductions']) {
                (frm.doc[table] || []).forEach((row, index) => {
                    const updates = Object.assign({}, values[table][index]);
                    for (const field of ['name', 'doctype', 'parent', 'parentfield', 'parenttype', 'idx', 'owner', 'creation', 'modified', 'modified_by']) delete updates[field];
                    Object.assign(row, updates);
                });
            }
            frm.refresh_fields();
        }, 300);
        frm._calculate_subcontract_totals();
    },
    project: recalculate, currency: recalculate, conversion_rate: recalculate, discount_amount: recalculate,
    additional_discount_percentage: recalculate, apply_discount_on: recalculate, disable_rounded_total: recalculate
};
for (const type of commercial_types) frappe.ui.form.on(type, handlers);
frappe.ui.form.on('Deduction', {percent: recalculate, account: recalculate, deductions_remove: recalculate});
frappe.ui.form.on('Purchase Taxes and Charges', {
    rate: recalculate, tax_amount: recalculate, charge_type: recalculate, taxes_remove: recalculate,
    row_id: recalculate, included_in_print_rate: recalculate, add_deduct_tax: recalculate,
    async account_head(frm, cdt, cdn) {
        if (!commercial_types.includes(frm.doctype) || frm.doc.docstatus) return;
        const row = locals[cdt][cdn];
        const account = row.account_head;
        if (account && !row.description) {
            const r = await frappe.db.get_value('Account', account, 'account_name');
            if (row.account_head !== account) return;
            if (!row.description && r.message) await frappe.model.set_value(cdt, cdn, 'description', r.message.account_name || account);
        }
        recalculate(frm);
    }
});
}
