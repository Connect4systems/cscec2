frappe.ui.form.on('Comparison', {
  onload(frm) {
    frm.comparison_table_data = frm.doc.comparison_table_data_json
      ? JSON.parse(frm.doc.comparison_table_data_json)
      : { items: [], suppliers: [], prices: [] };

    frappe.call({
      method: "frappe.client.get_list",
      args: { doctype: "Supplier", fields: ["name"], limit_page_length: 999 },
      callback(r) {
        frm.all_suppliers = r.message.map(s => s.name).sort();
        render_comparison_table(frm);
      }
    });
  },

  refresh(frm) {
    frm.save_comparison_data = () => {
      frm.set_value("comparison_table_data_json", JSON.stringify(frm.comparison_table_data));
    };

    frm.add_custom_button("Attach Supplier", () => {
      const dialog = new frappe.ui.Dialog({
        title: "Attach Supplier",
        fields: [{ label: "Supplier", fieldname: "supplier", fieldtype: "Link", options: "Supplier", reqd: true }],
        primary_action({ supplier }) {
          frm.comparison_table_data.suppliers.push(supplier);
          frm.comparison_table_data.prices.forEach(row => row.push({ rate: 0, amount: 0 }));
          frm.add_child("supplier_comparison", { supplier });
          frm.refresh_field("supplier_comparison");
          frm.save_comparison_data();
          render_comparison_table(frm);
          dialog.hide();
        }
      });
      dialog.show();
    });

    frm.add_custom_button("Export Excel", () => {
      const { suppliers, items, prices } = frm.comparison_table_data;
      let csv = [
        ["Item", "Description", "Qty", "UOM", "Cost Note", ...suppliers.flatMap(s => [s + " Rate", s + " Amount"])]
      ];
      items.forEach((row, idx) => {
        const priceRow = prices[idx] || [];
        csv.push([
          row.item, row.description, row.qty, row.uom, row.cost_note,
          ...priceRow.flatMap(p => [p.rate, p.amount])
        ]);
      });
      const csvContent = csv.map(e => e.join(",")).join("\n");
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `${frm.doc.name}_Comparison.csv`;
      link.click();
    });

    render_comparison_table(frm);
  }
});

function render_comparison_table(frm) {
  const wrapper = frm.fields_dict.comparison_table.$wrapper;
  const { items, suppliers, prices } = frm.comparison_table_data;

  while (prices.length < items.length) {
    prices.push(suppliers.map(() => ({ rate: 0, amount: 0 })));
  }

  let html = `<div style="overflow-x:auto;">
    <table class="table table-bordered" style="min-width:1400px; width:100%;">
    <thead><tr>
      <th style="width:3%"></th>
      <th style="width:10%">Item</th>
      <th style="width:15%">Description</th>
      <th style="width:5%">Qty</th>
      <th style="width:5%">UOM</th>
      <th style="width:10%">Cost Note</th>`;

  suppliers.forEach((s) => {
    html += `<th colspan="2" style="width:15%">
      <div>${s}</div>
      <div style='display:flex; align-items:center; justify-content:space-between;'>
        <div style='width:50%'>Rate</div>
        <div style='width:50%'>Amount</div>
      </div>
    </th>`;
  });

  html += `</tr></thead><tbody>`;

  items.forEach((item, rowIdx) => {
    html += `<tr>
      <td><input type="checkbox" class="row-check" data-row="${rowIdx}"></td>
      <td><div id="item-${rowIdx}"></div></td>
      <td>${item.description || ""}</td>
      <td contenteditable="true" data-row="${rowIdx}" data-field="qty">${item.qty || ""}</td>
      <td>${item.uom || ""}</td>
      <td contenteditable="true" data-row="${rowIdx}" data-field="cost_note">${item.cost_note || ""}</td>`;

    suppliers.forEach((_, colIdx) => {
      const cell = prices[rowIdx][colIdx] || { rate: 0, amount: 0 };
      html += `<td colspan="2">
        <div style='display:flex;'>
          <div contenteditable="true" data-rate-row="${rowIdx}" data-rate-col="${colIdx}" style='width:50%'>${cell.rate}</div>
          <div style='width:50%'>${cell.amount}</div>
        </div>
      </td>`;
    });
    html += `</tr>`;
  });

  html += `<tr><td colspan="6"><strong>Total</strong></td>`;
  suppliers.forEach((_, colIdx) => {
    let total = 0;
    prices.forEach(row => total += parseFloat(row[colIdx]?.amount || 0));
    html += `<td colspan="2"><strong>${total.toFixed(2)}</strong></td>`;
  });
  html += `</tr></tbody></table></div>
    <button class="btn btn-sm btn-success" id="add-row">Add Item</button>
    <button class="btn btn-sm btn-danger" id="delete-selected" style="margin-left: 10px;">Delete Selected Rows</button>`;

  wrapper.html(html);

  // Render item selector
    setTimeout(() => {
    items.forEach((item, idx) => {
      wrapper.find(`#item-${idx}`).empty();

      const field = frappe.ui.form.make_control({
        parent: wrapper.find(`#item-${idx}`),
        df: {
          fieldtype: "Link",
          options: "Item",
          fieldname: `item_${idx}`,
          placeholder: "Select Item"
        },
        only_input: true,
        render_input: true
      });

      field.make_input();
      field.set_value(item.item || "");

      field.$input.on("blur", () => {
        const val = field.get_value();
        if (!val) return;

        frappe.db.get_doc("Item", val).then(doc => {
          frm.comparison_table_data.items[idx] = {
            ...frm.comparison_table_data.items[idx],
            item: doc.name,
            description: doc.description,
            uom: doc.stock_uom
          };
          frm.save_comparison_data();
          render_comparison_table(frm);
        });
      });
    });
  }, 100);

  // Save on blur
  wrapper.find('[contenteditable="true"]').on('blur', function () {
    const el = $(this);
    const row = +el.data('row');
    const field = el.data('field');
    const rateRow = +el.data('rate-row');
    const rateCol = +el.data('rate-col');

    if (!isNaN(row) && field) {
      frm.comparison_table_data.items[row][field] = el.text();
    }

    if (!isNaN(rateRow) && !isNaN(rateCol)) {
      const rate = parseFloat(el.text()) || 0;
      const qty = parseFloat(frm.comparison_table_data.items[rateRow].qty) || 0;
      frm.comparison_table_data.prices[rateRow][rateCol] = { rate, amount: qty * rate };
    }

    frm.save_comparison_data();
  });

  // Add Row
  wrapper.find('#add-row').on('click', () => {
    frm.comparison_table_data.items.push({
      item: "", description: "", qty: "", uom: "", cost_note: ""
    });
    frm.comparison_table_data.prices.push(
      frm.comparison_table_data.suppliers.map(() => ({ rate: 0, amount: 0 }))
    );
    frm.save_comparison_data();
    render_comparison_table(frm);
  });

  // Delete selected rows
  wrapper.find('#delete-selected').on('click', () => {
    const selectedRows = wrapper.find('.row-check:checked').map(function () {
      return parseInt($(this).data('row'));
    }).get();

    if (selectedRows.length === 0) {
      frappe.msgprint("No rows selected.");
      return;
    }

    frm.comparison_table_data.items = frm.comparison_table_data.items.filter((_, idx) => !selectedRows.includes(idx));
    frm.comparison_table_data.prices = frm.comparison_table_data.prices.filter((_, idx) => !selectedRows.includes(idx));

    frm.save_comparison_data();
    render_comparison_table(frm);
  });
}
