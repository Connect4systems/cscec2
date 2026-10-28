const cr_clause_api = 'contractor.contractor_app.doctype.cr.cr.';

frappe.ui.form.on('CR', {
    refresh(frm) {
        frm.fields_dict.clauses.grid.update_docfield_property('series_number', 'read_only', frm.doc.numbering_mode !== 'From Excel');
        if (frm.doc.docstatus !== 0) return;
        frm.add_custom_button(__('Excel Template'), () => window.open('/api/method/' + cr_clause_api + 'download_template'));
        if (frm.is_new()) return;
        const saved = () => {
            if (!frm.is_dirty()) return true;
            frappe.msgprint(__('Save the CR first'));
            return false;
        };
        frm.add_custom_button(__('Fetch from Project'), () => {
            if (!saved()) return;
            frappe.confirm(__('Replace current clauses with clauses from the selected Project?'), async () => {
                await frappe.call({method: cr_clause_api + 'fetch_project_clauses', args: {cr: frm.doc.name}, freeze: true});
                await frm.reload_doc();
            });
        });
        frm.add_custom_button(__('Upload Excel'), () => {
            if (!saved()) return;
            new frappe.ui.FileUploader({
                doctype: frm.doctype, docname: frm.doc.name, is_private: 1,
                restrictions: {allowed_file_types: ['.xlsx']},
                on_success: async file => {
                    const result = await frappe.call({method: cr_clause_api + 'preview_excel', args: {cr: frm.doc.name, file_url: file.file_url}});
                    const esc = frappe.utils.escape_html;
                    const html = '<div style="max-height:400px;overflow:auto"><table class="table"><thead><tr><th>Series</th><th>Title</th><th>Group</th><th>Qty</th><th>UOM</th></tr></thead><tbody>' +
                        result.message.map(row => '<tr>' + [row.series_number, row.clause_title, row.is_group, row.qty, row.uom || ''].map(value => '<td>' + esc(String(value)) + '</td>').join('') + '</tr>').join('') + '</tbody></table></div>';
                    const dialog = new frappe.ui.Dialog({title: __('Preview Excel — replace current rows'), size: 'extra-large',
                        fields: [{fieldname: 'preview', fieldtype: 'HTML', options: html}],
                        primary_action_label: __('Apply Rows'),
                        primary_action: async () => {
                            if (!saved()) return;
                            await frappe.call({method: cr_clause_api + 'apply_excel', args: {cr: frm.doc.name, file_url: file.file_url}, freeze: true});
                            dialog.hide();
                            await frm.reload_doc();
                        }});
                    dialog.show();
                }
            });
        });
    },
    numbering_mode(frm) {
        frm.fields_dict.clauses.grid.update_docfield_property('series_number', 'read_only', frm.doc.numbering_mode !== 'From Excel');
    }
});
