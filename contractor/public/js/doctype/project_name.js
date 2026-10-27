frappe.provide('contractor');
contractor.fetch_project_name = contractor.fetch_project_name || function(frm) {
    if (frm.is_new() || frm.doc.docstatus === 2 || frm.doc.project || frm.doc.created_project || !frm.fields_dict.project) return;
    const name = frm.doc.name;
    frappe.call({method: 'contractor.project_names.get_project_name', args: {doctype: frm.doctype, name},
        callback(r) {
            if (r.message && frm.doc.name === name && !frm.doc.project) frm.set_value('project', r.message);
        }});
};
