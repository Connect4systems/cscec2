frappe.ui.form.on("Project Contract", {
    refresh(frm) {
        frm.fields_dict.clauses.grid.cannot_add_rows = true;
        frm.fields_dict.clauses.grid.cannot_delete_rows = true;
    },
    setup(frm) {
        for (const [table, field] of [['taxes', 'account_head'], ['deductions', 'account']]) {
            frm.set_query(field, table, () => ({filters: {company: frm.doc.company, is_group: 0}}));
        }
    },
    async selling_deductions_template(frm) {
        if (!frm.doc.selling_deductions_template) return;
        const r = await frappe.call({method: 'contractor.www.api.get_deductions',
            args: {master_doctype: 'Selling Deductions Template', master_name: frm.doc.selling_deductions_template}});
        frm.clear_table('deductions');
        for (const row of r.message || []) frm.add_child('deductions', row);
        frm.refresh_field('deductions');
        frm.dirty();
    },
    async tc_name(frm) {
        if (!frm.doc.tc_name) return;
        const r = await frappe.db.get_value('Terms and Conditions', frm.doc.tc_name, 'terms');
        frm.set_value('terms', r.message.terms || '');
    }
});
