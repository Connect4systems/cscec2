import frappe

def share_project_users(doc, method):
    """Auto-share the Project with selected Employees' User IDs after save."""

    # ✅ Project Manager
    if doc.custom_project_manager:
        user_id = frappe.db.get_value("Employee", doc.custom_project_manager, "user_id")
        if not user_id:
            frappe.throw("⚠️ Project Manager has no User ID.")
        email = frappe.db.get_value("User", user_id, "email")
        if not email:
            frappe.throw("⚠️ Project Manager User has no Email.")
        _share_project(doc.name, user_id)

    # ✅ Technical Office
    if doc.custom_technical_office:
        user_id = frappe.db.get_value("Employee", doc.custom_technical_office, "user_id")
        if not user_id:
            frappe.throw("⚠️ Technical Office Employee has no User ID.")
        email = frappe.db.get_value("User", user_id, "email")
        if not email:
            frappe.throw("⚠️ Technical Office User has no Email.")
        _share_project(doc.name, user_id)

def _share_project(project, user_id):
    """Share Project Read-Only with given User ID if not already shared."""
    if not frappe.db.exists("DocShare", {
        "share_doctype": "Project",
        "share_name": project,
        "user": user_id
    }):
        frappe.share.add(
            doctype="Project",
            name=project,
            user=user_id,
            read=1,
            write=0,
            share=0
        )

@frappe.whitelist()
def create_material_issue(docname):
    """Create a Stock Entry (Material Issue) from a Site Material Request."""

    # ✅ Get Site Material Request
    smr = frappe.get_doc('Site Material Request', docname)

    # ✅ Create Stock Entry
    se = frappe.new_doc('Stock Entry')
    se.stock_entry_type = 'Material Issue'
    se.project = smr.project                      # Header Project
    se.custom_site_material_request = smr.name    # Link back to SMR

    for item in smr.material_request:
        se.append('items', {
            'item_code': item.item,
            'qty': item.qty,
            'uom': frappe.db.get_value('Item', item.item, 'stock_uom'),
            's_warehouse': smr.warehouse,
            'project': smr.project,               # ✅ Dimension: project for this row
            'cost_code': item.cost_code
        })

    # ✅ Insert as Draft
    se.insert(ignore_permissions=True)
    frappe.msgprint(f'Stock Entry {se.name} created')
    return se.name
