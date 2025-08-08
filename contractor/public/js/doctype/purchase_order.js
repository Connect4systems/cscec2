
{% include 'erpnext/buying/doctype/purchase_order/purchase_order.js' %}

frappe.provide("contractor");
frappe.provide("contractor.buying");

contractor.buying.CustomPurchaseOrderController = class CustomPurchaseOrderController extends erpnext.buying.PurchaseOrderController {
    refresh(doc, dt, dn){
        var me = this;
		super.refresh(doc, dt, dn);
        // cur_frm.remove_custom_button('Project', 'Create');
        // if(flt(doc.per_delivered, 2) < 100) {
        //     this.frm.add_custom_button(__('Project'), () => this.make_project(), __('Create'));
        // }
        if (this.frm.doc.docstatus == 1){
            me.frm.add_custom_button(__("Purchase Clearence"), () => {
                this.create_clearence();
            }, __('Create'))
        }
        // else if (this.frm.doc.docstatus == 0){
        //     me.frm.add_custom_button(__("Costing Note"), () => {
        //         this.create_costing_note();
        //     }, __('Create'))
        // }
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
    make_project() {
		frappe.model.open_mapped_doc({
			method: "contractor.www.api.make_project",
			frm: this.frm,
            args: {
                doctype: "Purchase Order"
            }
		})
	}
    create_clearence(){
        frappe.model.open_mapped_doc({
			method: "contractor.www.api.create_purchase_clearence",
			frm: this.frm
		})
    }
    create_costing_note(){
        frappe.model.open_mapped_doc({
			method: "contractor.www.api.create_costing_note",
			frm: this.frm,
            args: {
                doctype: "Purchase Order"
            }
		})
    }
}

extend_cscript(cur_frm.cscript, new contractor.buying.CustomPurchaseOrderController({frm: cur_frm}));

frappe.ui.form.on("Deduction", {
    percent: function(frm, cdt, cdn){
        let row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, "value", row.percent * frm.doc.rounded_total / 100);
    }
})