frappe.ui.form.on("Project Contract", {
    refresh(frm) {
        frm.fields_dict.clauses.grid.cannot_add_rows = true;
        frm.fields_dict.clauses.grid.cannot_delete_rows = true;
        if (frm.doc.docstatus === 0) frm.trigger('recalculate_contract_totals');
    },
    setup(frm) {
        for (const [table, field] of [['taxes', 'account_head'], ['deductions', 'account']]) {
            frm.set_query(field, table, () => ({filters: {company: frm.doc.company, is_group: 0}}));
        }
        frm.set_query('taxes_and_charges', () => ({filters: {company: frm.doc.company, disabled: 0}}));
        frm.set_query('cost_center', 'taxes', () => ({filters: {company: frm.doc.company, is_group: 0}}));
    },
    recalculate_contract_totals(frm) {
        frm._contract_totals_revision = (frm._contract_totals_revision || 0) + 1;
        if (!frm._calculate_contract_totals) {
            frm._calculate_contract_totals = frappe.utils.debounce(async () => {
                if (frm.doc.docstatus !== 0 || !frm.doc.company || !frm.doc.currency || !flt(frm.doc.conversion_rate)) return;
                const details = (frm.doc.clauses || []).filter(row => !row.is_group);
                if (!details.length || details.some(row => !flt(row.qty))) return;
                if ((frm.doc.taxes || []).some(row => !row.charge_type || !row.account_head)) return;
                const revision = frm._contract_totals_revision;
                const r = await frappe.call({method: 'contractor.project_contract_taxes.preview_totals',
                    args: {doc: JSON.stringify(frm.doc)}});
                if (!r.message || frm.doc.docstatus !== 0 || revision !== frm._contract_totals_revision) return;
                Object.assign(frm.doc, r.message.totals);
                for (const field of ['clauses', 'taxes', 'deductions']) {
                    (frm.doc[field] || []).forEach((row, index) => Object.assign(row, r.message[field][index] || {}));
                    frm.refresh_field(field);
                }
                for (const field of Object.keys(r.message.totals)) frm.refresh_field(field);
            }, 350);
        }
        frm._calculate_contract_totals();
    },
    before_save(frm) { frm._contract_totals_revision = (frm._contract_totals_revision || 0) + 1; },
    async taxes_and_charges(frm) {
        const template = frm.doc.taxes_and_charges;
        const company = frm.doc.company;
        if (!template) {
            frm.clear_table('taxes');
        } else {
            const r = await frappe.call({method: 'contractor.project_contract_taxes.get_sales_tax_template',
                args: {template, company}});
            if (frm.doc.taxes_and_charges !== template || frm.doc.company !== company) return;
            frm.clear_table('taxes');
            for (const row of r.message || []) frm.add_child('taxes', row);
        }
        frm.refresh_field('taxes');
        frm.dirty();
        frm.trigger('recalculate_contract_totals');
    },
    conversion_rate(frm) { frm.trigger('recalculate_contract_totals'); },
    currency(frm) { frm.trigger('recalculate_contract_totals'); },
    apply_discount_on(frm) { frm.trigger('recalculate_contract_totals'); },
    additional_discount_percentage(frm) { frm.trigger('recalculate_contract_totals'); },
    disable_rounded_total(frm) { frm.trigger('recalculate_contract_totals'); },
    discount_amount(frm) {
        if (flt(frm.doc.additional_discount_percentage)) frm.set_value('additional_discount_percentage', 0);
        frm.trigger('recalculate_contract_totals');
    },
    async selling_deductions_template(frm) {
        if (!frm.doc.selling_deductions_template) return;
        const r = await frappe.call({method: 'contractor.www.api.get_deductions',
            args: {master_doctype: 'Selling Deductions Template', master_name: frm.doc.selling_deductions_template}});
        frm.clear_table('deductions');
        for (const row of r.message || []) frm.add_child('deductions', row);
        frm.refresh_field('deductions');
        frm.dirty();
        frm.trigger('recalculate_contract_totals');
    },
    async tc_name(frm) {
        if (!frm.doc.tc_name) return;
        const r = await frappe.db.get_value('Terms and Conditions', frm.doc.tc_name, 'terms');
        frm.set_value('terms', r.message.terms || '');
    }
});

frappe.ui.form.on('Project Contract Clause', {
    qty(frm) { frm.trigger('recalculate_contract_totals'); },
    rate(frm) { frm.trigger('recalculate_contract_totals'); }
});

const recalculate_project_contract = frm => {
    if (frm.doctype === 'Project Contract') frm.trigger('recalculate_contract_totals');
};
frappe.ui.form.on('Sales Taxes and Charges', {
    charge_type: recalculate_project_contract,
    rate: recalculate_project_contract,
    tax_amount: recalculate_project_contract,
    row_id: recalculate_project_contract,
    included_in_print_rate: recalculate_project_contract,
    taxes_add: recalculate_project_contract,
    taxes_remove: recalculate_project_contract,
    async account_head(frm, cdt, cdn) {
        if (frm.doctype !== 'Project Contract') return;
        const row = locals[cdt][cdn];
        const account = row.account_head;
        if (account) {
            const r = await frappe.db.get_value('Account', account, ['account_name', 'account_currency', 'tax_rate']);
            if (row.account_head !== account) return;
            const values = {description: r.message.account_name, account_currency: r.message.account_currency};
            if (row.charge_type === 'On Net Total') values.rate = flt(r.message.tax_rate);
            await frappe.model.set_value(cdt, cdn, values);
        }
        recalculate_project_contract(frm);
    }
});
frappe.ui.form.on('Deduction', {
    percent: recalculate_project_contract,
    deductions_add: recalculate_project_contract,
    deductions_remove: recalculate_project_contract
});
