frappe.ui.form.on("Project", {
    refresh: function(frm){
        if (!frm.is_new() && frm.doc.status !== 'Cancelled') {
            frm.add_custom_button(__('Subcontract Clearnce'),
                () => frm.events.create_subcontract_clearance(frm), __('Create'));
        }
        if (frm.doc.project_contract) {
            frm.set_df_property('custom_contract_items', 'hidden', 1);
            for (const field of frm.meta.fields) {
                if (field.fieldtype === 'Currency') frm.set_df_property(field.fieldname, 'hidden', 1);
            }
            frm.add_custom_button(__('Project Contract'), () => frappe.set_route('Form', 'Project Contract', frm.doc.project_contract));
            frm.add_custom_button(__('Project Clearnce'), () => frm.events.create_clause_clearance(frm, 'Project Clearnce'), __('Create'));
            return;
        }
        frm.set_query("item_code", "items", function(doc, cdt, cdn) {
			let row = locals[cdt][cdn];
            return {
				filters: {
					is_group: row.is_group
				}
			}
		});
        frm.add_custom_button(__("Project Clearnce"),
            () => {frm.events.create_clearence(frm)}, 
            "Create")

        frm.add_custom_button(__("Costing Note"), 
            () => {frm.events.create_costing_note(frm)}, 
            "Create")
    },
    async create_subcontract_clearance(frm) {
        if (frm.is_dirty() || frm.is_new()) return frappe.msgprint(__('Save the Project first'));
        const project = frm.doc.name;
        const response = await frappe.call({method: 'contractor.subcontracting.project_contract_options', args: {project}});
        if (frm.doc.name !== project) return;
        const options = response.message;
        if (!options.suppliers.length) return frappe.msgprint(__('No submitted Subcontractor Contracts are available for this Project.'));
        let creating = false;
        let dialog;
        dialog = new frappe.ui.Dialog({
            title: __('Create Subcontract Clearnce'),
            fields: [
                {fieldname: 'supplier', fieldtype: 'Link', options: 'Supplier', label: __('Supplier'), reqd: 1,
                    get_query: () => ({filters: {name: ['in', options.suppliers.map(row => row.name)]}}),
                    onchange: () => {
                        if (dialog) dialog.set_value('subcontractor_contract', null);
                    }},
                {fieldname: 'subcontractor_contract', fieldtype: 'Link', options: 'Subcontractor Contract',
                    label: __('Subcontractor Contract'), reqd: 1,
                    depends_on: 'eval:!!doc.supplier',
                    get_query: () => ({filters: {project, docstatus: 1, supplier: dialog.get_value('supplier'),
                        name: ['in', options.contracts.filter(row => row.supplier === dialog.get_value('supplier')).map(row => row.name)]}})}
            ],
            primary_action_label: __('Create Clearance'),
            primary_action: async values => {
                if (creating || frm.is_dirty() || frm.doc.name !== project) return frappe.msgprint(__('Save the Project and reopen this action'));
                if (!values.supplier || !values.subcontractor_contract) return;
                creating = true;
                try {
                    const r = await frappe.call({method: 'contractor.subcontracting.create_clearance',
                        args: {project, supplier: values.supplier, subcontractor_contract: values.subcontractor_contract}, freeze: true});
                    dialog.hide();
                    const docs = frappe.model.sync(r.message);
                    frappe.set_route('Form', 'Subcontract Clearnce', docs[0].name);
                } finally { creating = false; }
            }
        });
        dialog.show();
    },
    async create_clause_clearance(frm, doctype, supplier) {
        if (frm.is_dirty() || frm.is_new()) return frappe.msgprint(__('Save the Project first'));
        const r = await frappe.call({method: 'contractor.project_clearances.create_clearance',
            args: {project: frm.doc.name, doctype, supplier: supplier || null}});
        const docs = frappe.model.sync(r.message);
        frappe.set_route('Form', doctype, docs[0].name);
    },
    create_costing_note(frm){
        frappe.model.open_mapped_doc({
			method: "contractor.www.api.create_costing_note",
			frm: frm,
            args: {
                doctype: "Project"
            }
		})
    },
    create_clearence: function(frm){
        frappe.model.open_mapped_doc({
			method: "contractor.www.api.create_clearence",
			frm: frm,
            args: {
                "doctype": "Project"
            }
		})
    },
    set_series_number: function(frm, row){
        let latest_group = 0;
        let latest_sub = 0;
        let group_item = null;
        
        // Iterate through the items table to get the latest Group/Sub item
        for (let i of frm.doc.items){
            /// if we get to our index then add +1 to the previous group/sub item
            if (i.idx == row.idx){
                if (row.is_group) latest_group += 1;
                
                else {
                    latest_sub += 1;
                }
                ///Set the Group Item to be the First Group Item Row
                if (!group_item) group_item = i.item_code;

                ///Set thee Group Item of the Current Item
                i.group_item = group_item;
                break;
            }

            else {
                if (i.is_group){
                    latest_group = parseInt(i.series_number)
                    latest_sub = 0;
                    if (i.group_item) group_item = i.group_item;
                    else group_item = i.item_code;
                }
                else if (i.series_number) {
                    [latest_group, latest_sub] = get_group_sub(i.series_number)
                }
            }
        }

        if (latest_group){
            if (row.is_group) row.series_number = latest_group;

            else row.series_number = latest_group + "_" + latest_sub;
        }
        frm.refresh_field("items");
    }
})
frappe.ui.form.on("Project Item", {
    is_group: function(frm ,cdt, cdn){
        let row = locals[cdt][cdn];
        if (row.is_group && row.item_code) {
            row.group_item = row.item_code;
            row.parent_group = row.item_code;
        }
        else {
            const index = frm.doc.items.length - 2;
            if (index < 0) return
            row.parent_group = frm.doc.items[index].parent_group;
        }
        frm.events.set_series_number(frm, row)
    },
    item_code: function(frm, cdt, cdn){
        let row = locals[cdt][cdn];
        if (row.is_group == 1) {
            row.group_item = row.item_code;
            row.parent_group = row.item_code
        }
        else {
            const index = frm.doc.items.length - 2;
            if (index < 0) return
            row.parent_group = frm.doc.items[index].parent_group;
        }
        frm.events.set_series_number(frm, row)
    },
    qty: function(frm, cdt, cdn){
        let row = locals[cdt][cdn];
        if (row.rate){
            frappe.model.set_value(cdt, cdn, "amount", row.rate * row.qty);
        }
    },
    rate: function(frm, cdt, cdn){
        let row = locals[cdt][cdn];
        if (row.qty){
            frappe.model.set_value(cdt, cdn, "amount", row.rate * row.qty);
        }
    },
    items_add: function(frm ,cdt, cdn){
        frappe.model.set_value(cdt, cdn, "rate", 0.00);
        frappe.model.set_value(cdt, cdn, "amount", 0.00);
        let row = locals[cdt][cdn];
        const index = frm.doc.items.length - 2;
        if (index < 0) return
        row.parent_group = frm.doc.items[index].parent_group;
    }
    
})

const get_group_sub = function(num_string){
    let numbers = num_string.match(/\d+/g); // Matches one or more consecutive digits
    return [parseInt(numbers[0]), parseInt(numbers[1])]
}
