{% include 'contractor/public/js/doctype/boq_resources.js' %}
{% include 'contractor/public/js/doctype/project_name.js' %}
// Copyright (c) 2024, Jenan Alfahham and contributors
// For license information, please see license.txt

frappe.ui.form.on('BOQ', {
    refresh(frm) {
        contractor.setup_boq_resources(frm);
        contractor.recalculate_boq_resources(frm);
        contractor.fetch_project_name(frm);
        frm.toggle_display('item', !frm.doc.tender_analysis);
        frm.toggle_display('contractual_clause', !!frm.doc.tender_analysis);
        frm.set_df_property('project_qty', 'read_only', !!frm.doc.tender_analysis);
    },
	setup: function(frm){
		frm.set_query("party_type", function() {
			return{
				"filters": {
					"name": ["in", ["Customer", "Lead", "Prospect"]],
				}
			}
		});
		frm.set_query("boq_template", function() {
			return{
				"filters": {
					...(frm.doc.tender_analysis ? {} : {item_code: frm.doc.item}),
				}
			}
		});
	},
	onload: function(frm){
        if (!frm.doc.docstatus && frm.doc.quantity_basis !== 'Project Quantity') {
            for (const table of ['material_costs', 'labor_costs', 'contractors_table', 'expenses_table', 'equipment_costs', 'custom_equipment']) {
                for (const row of frm.doc[table] || []) row.per_unit_qty = flt(row.qty);
            }
            frm.doc.quantity_basis = 'Project Quantity';
            frm.dirty();
        }
        contractor.setup_boq_resources(frm);
        contractor.recalculate_boq_resources(frm);
		frm.trigger('setup_queries');
	},
    project_qty(frm) { contractor.recalculate_boq_resources(frm); },
	boq_template: function(frm){
		if ((frm.doc.item || frm.doc.contractual_clause) && frm.doc.boq_template){
			frappe.call({
				"method": "contractor.contractor_app.doctype.boq.boq.set_boq_template",
				"args": {"boq_template": frm.doc.boq_template},
				callback: function(r){
					if (r.message) {
						frm.clear_table("material_costs");
						frm.clear_table("labor_costs");
						frm.clear_table("contractors_table");
						frm.clear_table("expenses_table");
                        frm.clear_table("equipment_costs");
                        if (frm.fields_dict.custom_equipment) frm.clear_table("custom_equipment");
						let keys = Object.keys(r.message);

						for (const table of keys){
							for (const row of r.message[table]){
								let c = frm.add_child(table);
								c.cost = row.cost;
								c.item = row.item;
								c.per_unit_qty = row.per_unit_qty == null ? row.qty : row.per_unit_qty;
								c.qty = row.qty;
								c.uom = row.uom;
								c.total_cost = row.total_cost;

								if (table == "material_costs") c.depreciasion_percentage = row.depreciasion_percentage;

								else c.uom = row.uom
							}
							
							frm.refresh_field(table);

						}
                        contractor.recalculate_boq_resources(frm);
					}
				}
			})
		}
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
		} else if (frm.doc.party_type == "Prospect") {
			frm.set_query('party_name', function() {
				return {
					filters: {
						"company": frm.doc.company
					}
				};
			});
		}
	}
});
