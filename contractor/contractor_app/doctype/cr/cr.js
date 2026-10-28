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
        frm.add_custom_button(__('Fetch from Project'), async () => {
            if (!saved()) return;
            await open_cr_project_clause_picker(frm, saved);
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


async function open_cr_project_clause_picker(frm, saved) {
    const response = await frappe.call({method: cr_clause_api + 'project_clause_options', args: {cr: frm.doc.name}});
    const source = response.message;
    if (!source.clauses.length) return frappe.msgprint(__('The selected Project has no contract clauses'));
    const groups = source.clauses.filter(row => row.is_group);
    const selected = new Set();
    const quantities = new Map();
    const group_select_all = new Map();
    const group_labels = groups.map(row => `${row.series_number} - ${row.clause_title}`);
    let current_details = [];
    let applying = false;
    let dialog;
    dialog = new frappe.ui.Dialog({
        title: __('Fetch from Project'), size: 'extra-large',
        fields: [
            {fieldname: 'fetch_all', fieldtype: 'Check', label: __('All Clauses'), default: 1,
                onchange: () => update_visibility()},
            {fieldname: 'clause_group', fieldtype: 'Select', label: __('Group Clause'),
                options: [''].concat(group_labels), depends_on: 'eval:!doc.fetch_all', onchange: () => render_details()},
            {fieldname: 'select_all', fieldtype: 'Check', label: __('Select All Clauses in This Group'),
                depends_on: 'eval:!doc.fetch_all',
                onchange: () => {
                    if (!dialog) return;
                    const checked = !!dialog.get_value('select_all');
                    group_select_all.set(dialog.get_value('clause_group'), checked);
                    for (const row of current_details) {
                        if (checked) selected.add(row.name);
                        else selected.delete(row.name);
                    }
                    render_details();
                }},
            {fieldname: 'details', fieldtype: 'HTML'},
            {fieldname: 'selection_count', fieldtype: 'HTML'},
            {fieldname: 'replacement_notice', fieldtype: 'HTML',
                options: '<p class="text-muted">' + __('Inserting replaces the current CR clause table. Group headings and source series are preserved.') + '</p>'}
        ],
        primary_action_label: __('Insert Clauses'),
        primary_action: async () => {
            if (applying || !saved()) return;
            const fetch_all = dialog.get_value('fetch_all') ? 1 : 0;
            if (!fetch_all && !selected.size) return frappe.msgprint(__('Select at least one detail clause'));
            if (!fetch_all && Array.from(selected).some(name => {
                const row = source.clauses.find(item => item.name === name);
                const qty = Number(quantities.has(name) ? quantities.get(name) : row.qty);
                return !Number.isFinite(qty) || qty <= 0;
            })) return frappe.msgprint(__('Selected clause quantities must be greater than zero'));
            applying = true;
            try {
                await frappe.call({method: cr_clause_api + 'fetch_project_clauses', freeze: true,
                    args: {cr: frm.doc.name, project: source.project, fetch_all,
                        selected_rows: JSON.stringify(Array.from(selected)),
                        quantities: JSON.stringify(Object.fromEntries(Array.from(selected).filter(name => quantities.has(name)).map(name => [name, quantities.get(name)])))}});
                dialog.hide();
                await frm.reload_doc();
            } finally {
                applying = false;
            }
        }
    });
    function update_visibility() {
        if (!dialog) return;
        const partial = !dialog.get_value('fetch_all');
        for (const field of ['clause_group', 'select_all', 'selection_count']) dialog.toggle_display(field, partial);
        render_details();
    }
    function render_details() {
        if (!dialog) return;
        const group_index = group_labels.indexOf(dialog.get_value('clause_group'));
        const group = groups[group_index];
        current_details = group ? source.clauses.filter(row => !row.is_group && row.parent_series === group.series_number) : [];
        const esc = value => frappe.utils.escape_html(String(value == null ? '' : value));
        const partial = !dialog.get_value('fetch_all');
        const select_group = !!group_select_all.get(dialog.get_value('clause_group'));
        dialog.toggle_display('clause_group', partial);
        dialog.toggle_display('select_all', partial);
        dialog.toggle_display('selection_count', partial);
        dialog.toggle_display('details', partial && !!group && !select_group);
        dialog.fields_dict.select_all.$input.prop('checked', select_group);
        const html = '<div style="max-height:350px;overflow:auto"><table class="table"><thead><tr><th></th><th>' +
            __('Series') + '</th><th>' + __('Clause') + '</th><th>' + __('Qty') + '</th><th>' + __('UOM') + '</th></tr></thead><tbody>' +
            current_details.map((row, index) => '<tr><td><input type="checkbox" class="cr-detail-choice" data-index="' + index + '" ' +
                (selected.has(row.name) ? 'checked' : '') + ' aria-label="' + esc(row.clause_title) + '"></td><td>' +
                esc(row.series_number) + '</td><td>' + esc(row.clause_title) + '</td><td><input type="number" class="form-control cr-detail-qty" data-index="' + index + '" min="0" step="any" aria-label="' + esc(__('Qty')) + '" value="' + esc(quantities.has(row.name) ? quantities.get(row.name) : row.qty) + '"></td><td>' + esc(row.uom) + '</td></tr>').join('') +
            '</tbody></table></div>';
        const wrapper = dialog.fields_dict.details.$wrapper;
        wrapper.html(group ? html : '<p class="text-muted">' + __('Choose a group to see its clauses.') + '</p>');
        wrapper.find('.cr-detail-choice').on('change', function () {
            const row = current_details[Number(this.dataset.index)];
            if (this.checked) selected.add(row.name);
            else selected.delete(row.name);
            render_details();
        });
        wrapper.find('.cr-detail-qty').on('input', function () {
            quantities.set(current_details[Number(this.dataset.index)].name, this.value);
        });
        dialog.fields_dict.selection_count.$wrapper.text(__('Selected detail clauses: {0}', [selected.size]));
    }
    dialog.show();
    update_visibility();
}
