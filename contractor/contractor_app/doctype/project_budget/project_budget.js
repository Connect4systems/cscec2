frappe.ui.form.on('Project Budget', {
    refresh(frm) {
        frm.fields_dict.clauses.grid.cannot_add_rows = true;
        frm.fields_dict.clauses.grid.cannot_delete_rows = true;
        if (frm.doc.project_contract) frm.add_custom_button(__('Project Contract'),
            () => frappe.set_route('Form', 'Project Contract', frm.doc.project_contract));
        if (frm.doc.project) frm.add_custom_button(__('Project'),
            () => frappe.set_route('Form', 'Project', frm.doc.project));
    }
});
