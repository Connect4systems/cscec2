// Copyright (c) 2024, Jenan Alfahham and contributors
// For license information, please see license.txt

frappe.provide("contractor.buying");

// {% include 'erpnext/public/js/controllers/buying.js' %};
cur_frm.cscript.tax_table = "Purchase Taxes and Charges";

erpnext.accounts.taxes.setup_tax_filters("Purchase Taxes and Charges");
erpnext.buying.setup_buying_controller();

frappe.ui.form.on('Purchase Clearence', {
	setup: function(frm){
		frm.set_query("taxes_and_charges", function() {
			return {
				filters: {'company': frm.doc.company }
			}
		});
	},
	onload: function(frm) {
		erpnext.queries.setup_queries(frm, "Warehouse", function() {
			return erpnext.queries.warehouse(frm.doc);
		});
	},
	company: function(frm) {
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},

});

contractor.PurchaseClearenceController = class PurchaseClearenceController extends erpnext.buying.BuyingController {
	setup(doc) {
		this.setup_posting_date_time_check();
		super.setup(doc);
	}
	refresh(doc, cdt, cdn) {
		var me = this;
		if (cur_frm.doc.docstatus == 1 && cur_frm.doc.purchase_order){
			cur_frm.add_custom_button(__('Create Invoice'), () => this.create_purchase_invoice());
		}
		super.refresh();
	}
	purchasing_deductions_template() {
		var me = this;
		if(this.frm.doc.purchasing_deductions_template) {
			return this.frm.call({
				method: "contractor.www.api.get_deductions",
				args: {
					"master_doctype": frappe.meta.get_docfield(this.frm.doc.doctype, "purchasing_deductions_template",
						this.frm.doc.name).options,
					"master_name": this.frm.doc.purchasing_deductions_template
				},
				callback: function(r) {
					if(!r.exc) {
						if(me.frm.doc.deductions) {
							for (let ded of r.message) {
								me.frm.add_child("deductions", ded);
							}

							refresh_field("deductions");
						} else {
							me.frm.set_value("deductions", r.message);
						}
					}
				}
			});
		}
	}
	create_purchase_invoice(){
		frappe.model.open_mapped_doc({
			method: "contractor.contractor_app.doctype.purchase_clearence.purchase_clearence.make_purchase_invoice",
			frm: cur_frm,
			freeze_message: __("Creating Invoice ...")
		})
	}
	items_on_form_rendered() {
		erpnext.setup_serial_or_batch_no();
	}
	items_add(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		this.frm.script_manager.copy_from_first_row("items", row, ["cost_center"]);
	}
    supplier() {
		var me = this;

		if (this.frm.doc.__onload && this.frm.doc.__onload.load_after_mapping) return;

		erpnext.utils.get_party_details(this.frm, "erpnext.accounts.party.get_party_details",
			{
				posting_date: this.frm.doc.posting_date,
				party: this.frm.doc.supplier,
				party_type: "Supplier",
				price_list: this.frm.doc.buying_price_list,
			}, function() {
				me.apply_pricing_rule();
			})
	}
};

// for backward compatibility: combine new and previous states
extend_cscript(cur_frm.cscript, new contractor.PurchaseClearenceController({frm: cur_frm}));

cur_frm.fields_dict['items'].grid.get_field('project').get_query = function(doc, cdt, cdn) {
	return {
		filters:[
			['Project', 'status', 'not in', 'Completed, Cancelled']
		]
	}
}

cur_frm.set_query("expense_account", "items", function(doc) {
	return {
		query: "erpnext.controllers.queries.get_expense_account",
		filters: {'company': doc.company }
	}
});

cur_frm.cscript.expense_account = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	if(d.idx == 1 && d.expense_account){
		var cl = doc.items || [];
		for(var i = 0; i < cl.length; i++){
			if(!cl[i].expense_account) cl[i].expense_account = d.expense_account;
		}
	}
	refresh_field('items');
}

cur_frm.fields_dict["items"].grid.get_field("cost_center").get_query = function(doc) {
	return {
		filters: {
			'company': doc.company,
			'is_group': 0
		}

	}
}

cur_frm.cscript.cost_center = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	if(d.cost_center){
		var cl = doc.items || [];
		for(var i = 0; i < cl.length; i++){
			if(!cl[i].cost_center) cl[i].cost_center = d.cost_center;
		}
	}
	refresh_field('items');
}

frappe.ui.form.on('Purchase Clearence Item', {
	qty_percentage: function(frm, cdt, cdn){
		const row = locals[cdt][cdn];
		if (row.qty){
			frappe.model.set_value(cdt, cdn, "qty", row.qty_percentage * row.qty / 100);
		}
	},
});

frappe.ui.form.on("Deduction", {
    percent: function(frm, cdt, cdn){
        let row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, "value", row.percent * frm.doc.rounded_total / 100);
    }
})
