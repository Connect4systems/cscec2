const tender_api = "contractor.contractor_app.doctype.tender_analysis.tender_analysis.";

frappe.ui.form.on("Tender Analysis", {
    refresh(frm) {
        frm.fields_dict.clauses.grid.update_docfield_property("series_number", "read_only", frm.doc.numbering_mode !== "From Excel");
        frm.add_custom_button(__("Excel Template"), () => {
            window.open("/api/method/" + tender_api + "download_template");
        });
        if (frm.is_new()) return;
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
