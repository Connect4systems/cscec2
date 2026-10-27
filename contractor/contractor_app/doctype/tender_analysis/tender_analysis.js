const tender_api = "contractor.contractor_app.doctype.tender_analysis.tender_analysis.";

frappe.ui.form.on("Tender Analysis", {
    setup(frm) {
        frm.set_query('account', 'deductions', () => ({filters: {company: frm.doc.company, is_group: 0}}));
    },
    async selling_deductions_template(frm) {
        const template = frm.doc.selling_deductions_template;
        const company = frm.doc.company;
        if (!template) return;
        const r = await frappe.call({method: 'contractor.deductions.get_selling_deductions',
            args: {template, company}});
        if (frm.doc.selling_deductions_template !== template || frm.doc.company !== company) return;
        frm.clear_table('deductions');
        for (const row of r.message || []) frm.add_child('deductions', row);
        frm.refresh_field('deductions');
        frm.dirty();
        frm.trigger('calculate_tender_deductions');
    },
    calculate_tender_deductions(frm) {
        let total = 0;
        for (const row of frm.doc.deductions || []) {
            row.value = flt(frm.doc.total_amount) * flt(row.percent) / 100;
            total += row.value;
        }
        frm.doc.total_deductions = total;
        frm.doc.net_payable = flt(frm.doc.total_amount) - total;
        for (const field of ['deductions', 'total_deductions', 'net_payable']) frm.refresh_field(field);
    },
    refresh(frm) {
        frm.trigger('calculate_tender_deductions');
        frm.fields_dict.clauses.grid.update_docfield_property("series_number", "read_only", frm.doc.numbering_mode !== "From Excel");
        frm.add_custom_button(__("Excel Template"), () => {
            window.open("/api/method/" + tender_api + "download_template");
        });
        if (frm.is_new()) return;
        frappe.call({method: 'contractor.project_offer.creation_status',
            args: {tender_analysis: frm.doc.name},
            callback(r) {
                if (!r.message || !r.message.ready) return;
                frm.add_custom_button(__('Project Offer'), async () => {
                    if (frm.is_dirty()) return frappe.msgprint(__('Save the Tender Analysis first'));
                    const result = await frappe.call({method: 'contractor.project_offer.create_project_offer',
                        args: {tender_analysis: frm.doc.name}, freeze: true});
                    if (result.message.existing) return frappe.set_route('Form', 'Project Offer', result.message.existing);
                    const docs = frappe.model.sync(result.message.doc);
                    frappe.set_route('Form', 'Project Offer', docs[0].name);
                }, __('Create'));
            }});
        frappe.call({method: 'contractor.project_contract.creation_status',
            args: {tender_analysis: frm.doc.name},
            callback(r) {
                if (!r.message || !r.message.ready) return;
                frm.add_custom_button(__('Project Contract'), async () => {
                    if (frm.is_dirty()) return frappe.msgprint(__('Save the Tender Analysis first'));
                    const result = await frappe.call({method: 'contractor.project_contract.create_project_contract',
                        args: {tender_analysis: frm.doc.name}, freeze: true});
                    if (result.message.existing) return frappe.set_route('Form', 'Project Contract', result.message.existing);
                    const docs = frappe.model.sync(result.message.doc);
                    frappe.set_route('Form', 'Project Contract', docs[0].name);
                }, __('Create'));
            }});
        frappe.call({method: 'contractor.tender_pricing.get_submitted_boq_links',
            args: {tender_analysis: frm.doc.name},
            callback(r) {
                for (const row of frm.doc.clauses || []) {
                    row.submitted_boq = (r.message || {})[row.name] || null;
                }
                frm.refresh_field('clauses');
            }});
        const saved = () => {
            if (frm.is_dirty()) {
                frappe.msgprint(__("Save the Tender Analysis first"));
                return false;
            }
            return true;
        };
        frm.add_custom_button(__("Create Contractual Clauses"), async () => {
            if (!saved()) return;
            await frappe.call({method: tender_api + "create_contractual_clauses", args: {tender_analysis: frm.doc.name}, freeze: true});
            await frm.reload_doc();
        });
        if ((frm.doc.clauses || []).length && frm.doc.clauses.every(r => r.contractual_clause)) {
            frm.add_custom_button(__("Costing Note"), async () => {
                if (!saved()) return;
                const r = await frappe.call({method: tender_api + "create_costing_note", args: {tender_analysis: frm.doc.name}});
                const docs = frappe.model.sync(r.message);
                frappe.set_route("Form", "Costing Note", docs[0].name);
            }, __("Create"));
        }
        if (!(frm.doc.clauses || []).some(r => r.contractual_clause)) {
            frm.add_custom_button(__("Upload Excel"), () => {
                if (!saved()) return;
                new frappe.ui.FileUploader({
                    doctype: frm.doctype, docname: frm.doc.name, is_private: 1,
                    restrictions: {allowed_file_types: [".xlsx"]},
                    on_success: async file => {
                        const r = await frappe.call({method: tender_api + "preview_excel", args: {tender_analysis: frm.doc.name, file_url: file.file_url}});
                        const esc = frappe.utils.escape_html;
                        const html = '<div style="max-height:400px;overflow:auto"><table class="table"><thead><tr><th>Series</th><th>Title</th><th>Group</th><th>Qty</th><th>UOM</th></tr></thead><tbody>' +
                            r.message.map(row => '<tr>' + [row.series_number, row.clause_title, row.is_group, row.qty, row.uom || ""].map(v => '<td>' + esc(String(v)) + '</td>').join("") + '</tr>').join("") + '</tbody></table></div>';
                        const dialog = new frappe.ui.Dialog({title: __("Preview Excel — replace current rows"), size: "extra-large",
                            fields: [{fieldname: "preview", fieldtype: "HTML", options: html}],
                            primary_action_label: __("Apply Rows"),
                            primary_action: async () => {
                                await frappe.call({method: tender_api + "apply_excel", args: {tender_analysis: frm.doc.name, file_url: file.file_url}, freeze: true});
                                dialog.hide();
                                await frm.reload_doc();
                            }});
                        dialog.show();
                    }
                });
            });
        }
    },
    numbering_mode(frm) { frm.trigger("refresh"); }
});

frappe.ui.form.on('Deduction', {
    percent(frm) {
        if (frm.doctype === 'Tender Analysis') frm.trigger('calculate_tender_deductions');
    },
    deductions_add(frm) {
        if (frm.doctype === 'Tender Analysis') frm.trigger('calculate_tender_deductions');
    },
    deductions_remove(frm) {
        if (frm.doctype === 'Tender Analysis') frm.trigger('calculate_tender_deductions');
    }
});
