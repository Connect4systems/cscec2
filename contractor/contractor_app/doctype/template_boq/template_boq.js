{% include 'contractor/public/js/doctype/boq_resources.js' %}

frappe.ui.form.on('Template BOQ', {
    refresh(frm) { contractor.setup_boq_resources(frm); }
});
