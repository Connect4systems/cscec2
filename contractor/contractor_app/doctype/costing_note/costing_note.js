{% include 'contractor/public/js/doctype/project_name.js' %}
// Copyright (c) 2024, Jenan Alfahham and contributors
// For license information, please see license.txt

frappe.ui.form.on('Costing Note', {
    refresh(frm) {
        contractor.fetch_project_name(frm);
        const tender = !!frm.doc.tender_analysis;
        if (tender && !frm.is_new()) {
            frappe.call({method: 'contractor.tender_pricing.get_created_boq_links',
                args: {costing_note: frm.doc.name},
                callback(r) {
                    for (const row of frm.doc.costing_note_items || []) {
                        row.boq_reference = (r.message || {})[row.name] || null;
                    }
                    frm.refresh_field('costing_note_items');
                }});
        }
        for (const field of ['contractual_clause', 'clause_title']) {
            frm.fields_dict.costing_note_items.grid.update_docfield_property(field, 'hidden', !tender);
        }
        if (tender) {
            for (const field of ['is_group', 'qty', 'uom', 'series_number']) {
                frm.fields_dict.costing_note_items.grid.update_docfield_property(field, 'read_only', 1);
            }
            frm.fields_dict.costing_note_items.grid.cannot_add_rows = true;
            frm.fields_dict.costing_note_items.grid.cannot_delete_rows = true;
        }
    },
	setup: function(frm){
		frm.set_query("party_type", function() {
			return{
				"filters": {
					"name": ["in", ["Customer", "Supplier", "Lead", "Prospect"]],
				}
			}
		});

	},
	onload: function(frm){
		frm.trigger('setup_queries');
	},
	party_type: function(frm) {
		frm.trigger('setup_party_type');

		frm.set_value("party_name", "");
	},
	setup_party_type: function(frm) {
		frm.trigger('setup_queries');
		frm.trigger("set_dynamic_field_label");
	},
	set_dynamic_field_label: function(frm){
		if (frm.doc.party_type) {
			frm.set_df_property("party_name", "label", frm.doc.party_type);
		}
	},
	setup_queries: function(frm){
		if (frm.doc.party_type == "Lead") {
			frm.set_query('party_name', erpnext.queries['lead']);
		}
		else if (frm.doc.party_type == "Customer") {
			frm.set_query('party_name', erpnext.queries['customer']);
		} else if (frm.doc.party_type == "Supplier") {
			frm.set_query('party_name', erpnext.queries['supplier']);
		} else if (frm.doc.party_type == "Prospect") {
			frm.set_query('party_name', function() {
				return {
					filters: {
						"company": frm.doc.company
					}
				};
			});
		}
	},

})

frappe.ui.form.on('Costing Note Items', {
	boq: function(frm, cdt, cdn){
        let row = locals[cdt][cdn];
        if (frm.doc.tender_analysis) {
            if (frm.is_dirty() || frm.is_new()) return frappe.msgprint(__('Save the Costing Note first'));
            if (row.is_group) return frappe.msgprint(__('Group headings cannot be priced'));
            frappe.call({method: 'contractor.tender_pricing.create_clause_boq',
                args: {costing_note: frm.doc.name, row_name: row.name},
                callback(r) {
                    if (r.message.existing) frappe.set_route('Form', 'BOQ', r.message.existing);
                    else {
                        const docs = frappe.model.sync(r.message.doc);
                        frappe.set_route('Form', 'BOQ', docs[0].name);
                    }
                }});
            return;
        }
        frappe.model.open_mapped_doc({
			method: "contractor.www.api.create_boq",
			frm: frm,
			args: {
				"item_row": row
			}
		})
	},
	cost: function(frm, cdt, cdn){
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "total_cost", row.cost * row.qty);
	},
	total_cost: function(frm ,cdt, cdn){
		let row = locals[cdt][cdn];
		let total = row.total_cost + (row.total_cost * row.default_profit_margin / 100)
		frappe.model.set_value(cdt, cdn, "target_selling_price", total);
	},
	default_profit_margin: function(frm ,cdt, cdn){
		let row = locals[cdt][cdn];
		let total = row.total_cost + (row.total_cost * row.default_profit_margin / 100)
		frappe.model.set_value(cdt, cdn, "target_selling_price", total);
	},
	qty: function(frm, cdt, cdn){
        let row = locals[cdt][cdn];
        if (row.cost || frm.doc.tender_analysis){
            frappe.model.set_value(cdt, cdn, "total_cost", row.cost * row.qty);
        }
    },
});
