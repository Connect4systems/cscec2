frappe.ui.form.on("Material Request", {
    refresh: function(frm) {
        if (frm.doc.docstatus == 0) {
            frm.add_custom_button(
                __("BOQ"),
                () => frm.events.get_items_from_boq(frm),
                "Get Items From"
            );
        }

        if (
            frm.doc.docstatus === 0 &&
            frm.doc.workflow_state === "Pending Purchase" &&
            frm.doc.material_request_type === "Purchase" &&
            frappe.user.has_role("Purchase User")
        ) {
            frm.add_custom_button("Create Purchase Comparison", () => {
                // Filter selected items only
                const selected_items = frm.doc.items.filter(row => row.__checked === 1).map(row => ({
                    item: row.item_code,
                    description: row.description,
                    qty: row.qty,
                    uom: row.uom,
                    cost_note: ""
                }));

                if (selected_items.length === 0) {
                    frappe.msgprint(__("Please select at least one item in the table."));
                    return;
                }

                frappe.call({
                    method: "frappe.client.insert",
                    args: {
                        doc: {
                            doctype: "Comparison",
                            material_request: frm.doc.name,
                            company: frm.doc.company,
                            project: frm.doc.custom_project,
                            custom_required_date: frm.doc.schedule_date,
                            type: "Purchase",
                            comparison_table_data_json: JSON.stringify({
                                items: selected_items,
                                suppliers: [],
                                prices: selected_items.map(() => [])
                            })
                        }
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.set_route("Form", "Comparison", r.message.name);
                        }
                    }
                });
            });
        }
    },

    get_items_from_boq: function(frm) {
        // your existing code unchanged
    },

    custom_get_items: function(frm) {
        // your existing code unchanged
    }
});
