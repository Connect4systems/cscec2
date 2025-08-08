frappe.ui.form.on("Material Request", {
  refresh: function (frm) {
    if (
      frm.doc.docstatus !== 1 ||
      frm.doc.material_request_type !== "Purchase" ||
      frm.doc.workflow_state !== "Approved" ||
      !frappe.user.has_role("Purchase User")
    ) {
      return;
    }

    // ❌ Don't clear standard buttons!
    // frm.page.clear_primary_action();
    // frm.page.clear_inner_toolbar();

    frm.add_custom_button("Create Purchase Comparison", function () {
      let items = frm.doc.items.map(row => ({
        item: row.item_code,
        description: row.description,
        qty: row.qty,
        uom: row.uom,
        cost_note: ""
      }));

      frappe.call({
        method: "frappe.client.insert",
        args: {
          doc: {
            doctype: "Comparison",
            material_request: frm.doc.name,
            company: frm.doc.company,
            project: frm.doc.custom_project,
            
            comparison_table_data_json: JSON.stringify({
              items: items,
              suppliers: [],
              prices: []
            })
          }
        },
        callback: function (r) {
          if (!r.exc) {
            frm.set_value("custom_comparison", r.message.name);
            frm.save();
            frappe.set_route("Form", "Comparison", r.message.name);
          }
        }
      });
    });
  }
});
