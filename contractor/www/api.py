import frappe
from frappe.utils import today, flt
from frappe.model.mapper import get_mapped_doc

from contractor.contractor_app.doctype.boq.boq import set_boq_template

# Validation for the remaining contracting documents
def validate(doc, method=None):
    if doc.doctype in ("Opportunity", "Quotation", "Sales Order"):
        return
    if doc.doctype in ["Purchase Order", "Purchase Invoice", "Sales Invoice"]:
         calculate_project_discount_rates(doc)
    else:
        set_series_number(doc)
        set_rate_of_group_items(doc)
        if doc.doctype == "Project" or doc.doctype == "Sales Order":
            set_qtys(doc)
        if doc.doctype == "Sales Order":
            calculate_project_discount_rates(doc)

def on_update_after_submit(doc, method=None):
    if doc.doctype == "Purchase Order":
        set_qtys(doc)

def set_series_number(doc):
    """
    Set Series Number for each Item
    If item is an item group then the series would be like: '1, 2, 3...'
    If not then the series would be like: '1_1, 1_2, 2_1, 2_2....'
    """

    latest_group = 0
    latest_sub = 0
    group_item = None
    series = "series_number"
    if doc.doctype == "Clearence": series = "series"
    for item in doc.items:
        if item.is_group:
            latest_group += 1 
            if not item.get(series): setattr(item, series, latest_group)
            latest_sub = 0
            if item.group_item: 
                group_item = item.group_item
            else: group_item = item.item_code

        else:
            if latest_group == 0: continue
            latest_sub += 1
            if not item.get(series):
                setattr(item, series, str(latest_group) + "_" + str(latest_sub))

        item.group_item = group_item

def set_rate_of_group_items(doc):
    """
    Set rate for the group items which equals 
    the total amount of its sub items
    """
    rates = {}
    series = "series_number"
    if doc.doctype == "Clearence": series = "series"
    for item in doc.items:
        if not item.is_group and item.get(series):
            group = int(item.get(series).split('_')[0])

            if not rates.get((item.group_item, group)): 
                rates[(item.group_item, group)] = [0, 0]

            rates[(item.group_item, group)][0] += flt(item.amount)
            rates[(item.group_item, group)][1] += flt(item.qty)
        
        elif item.get(series): 
            item.rate = item.base_rate = item.amount = item.base_amount = 0

    doc.group_items = []

    for group_item, group in rates:
        new_item = frappe._dict({
            "group_item": group_item,
            "rate": rates[(group_item, group)][0],
            "base_rate": rates[(group_item, group)][0] * doc.conversion_rate if doc.doctype == "Opportunity" else rates[(group_item, group)][0],
            "qty": rates[(group_item, group)][1],
            "completed_qty": 0,
            "completion_percentage": 0
        })
        doc.append("group_items", new_item)

def calculate_project_discount_rates(doc):
    doc.total_deductions = 0
    for d in doc.get("deductions"):
        d.value = flt(doc.rounded_total * d.percent / 100, doc.precision("rounded_total"))
        doc.total_deductions += d.value

    doc.base_total_deductions = doc.total_deductions * doc.conversion_rate

def set_qtys(doc):
    if doc.doctype == "Project":
        cleas = frappe.db.get_all("Clearence", {"project": doc.name, "docstatus": 1}, "name")
    elif doc.doctype == "Sales Order":
        cleas = frappe.db.get_all("Clearence", {"sales_order": doc.name, "docstatus": 1}, "name")

    groups = {}
    for clea in cleas:
        d = frappe.get_doc("Clearence", clea.name)
        for item in d.items:
            if item.is_group: continue

            if not groups.get(item.group_item):
                groups[item.group_item] = 0

            groups[item.group_item] += item.qty

    for parent in doc.group_items:
        if groups.get(parent.group_item):
            parent.completed_qty = groups[parent.group_item]
            parent.completion_percentage = parent.completed_qty / parent.qty * 100

            frappe.db.set_value("Group Item", parent.name, "completed_qty", parent.completed_qty)
            frappe.db.set_value("Group Item", parent.name, "completion_percentage", parent.completion_percentage)


@frappe.whitelist()
def make_project(source_name, target_doc=None):
    doctype = frappe.flags.args.doctype

    def postprocess(source, doc):
        doc.project_type = "External"
        doc.project_name = source.name

    if doctype == "Sales Order":
        doc = get_mapped_doc(
            "Sales Order",
            source_name,
            {
                "Sales Order": {
                    "doctype": "Project",
                    "validation": {"docstatus": ["=", 1]},
                    "field_map": {
                        "name": "sales_order",
                        "base_grand_total": "estimated_costing",
                        "net_total": "total_sales_amount",
                        "grand_total": "project_amount",
                        "base_grand_total": "base_project_amount"
                    },
                },
                "Sales Order Item": {
                    "doctype": "Project Item",
                },

            },
            target_doc,
            postprocess,
        )

    return doc

@frappe.whitelist()
def create_costing_note(source_name, target_doc=None):
    doctype = frappe.flags.args.doctype

    if doctype not in ("Project", "Purchase Order"):
        frappe.throw("Create tender pricing from Tender Analysis")

    if doctype == "Project":
        field_map = {"name": "source_project", "project_name": "project", "customer": "party_name"}

    elif doctype == "Sales Order":
        field_map = {"name": "sales_order", "customer": "party_name"}

    elif doctype == "Purchase Order":
        field_map = {"name": "purchase_order", "supplier": "party_name"}

    def update_item(source, target, source_parent):
        if not target.item_group:
            target.item_group = frappe.db.get_value("Item", target.item, "item_group")


    doc = get_mapped_doc(
        doctype,
        source_name,
        {
            doctype: {
                "doctype": "Costing Note",
                "field_map": field_map,
            },
            doctype + " Item": {
                "doctype": "Costing Note Items",
                "field_map": {"item_code": "item", "amount": "target_selling_price"},
                #"condition": lambda doc: not doc.is_group,
                "postprocess": update_item,
            },
            "Group Item": {
                "doctype": "Group Item"
            },
        },
        target_doc,
    )

    if doctype == "Sales Order" or doctype == "Project": doc.party_type = "Customer"
    elif doctype == "Purchase Order": doc.party_type = "Supplier"
    return doc


@frappe.whitelist()
def create_boq(source_name, target_doc=None):
    item = frappe.flags.args.item_row
    item = frappe._dict(item)
    def set_missing_values(source, target):
        target.naming_series = "BOQ-.YYYY.-"
        target.group_item = item.group_item
        target.item = item.item
        target.unit = item.uom
        target.project_qty = item.qty
        target.start_date = today()
        target.line_id = item.name

    doc = get_mapped_doc(
        "Costing Note",
        source_name,
        {
            "Costing Note": {
                "doctype": "BOQ",
            },
        },
        target_doc,
        set_missing_values,
    )

    return doc

@frappe.whitelist()
def create_clearence(source_name, target_doc=None):
    doctype = frappe.flags.args.doctype

    def set_missing_values(source, target):
        
        if doctype == "Sales Order" and source.project:
            project = frappe.get_doc("Project", source.project)
            target.contract_date = project.date

        if doctype == "Sales Order":
            for item in source.items:
                if item.prevdoc_docname:
                    if frappe.db.exists("Quotation", item.prevdoc_docname):
                        quotation = frappe.get_doc("Quotation", item.prevdoc_docname)
                        if quotation.opportunity:
                            target.opportunity = quotation.opportunity
                            
                    break

    if doctype == "Sales Order":
        doclist = get_mapped_doc(
            "Sales Order",
            source_name,
            {
                "Sales Order": {
                    "doctype": "Clearence", 
                    "validation": {"docstatus": ["=", 1]},
                    "field_map": {
                        "transaction_date": "posting_date",
                        "name": "sales_order",
                        "delivery_date": "delivery_date"
                    }
                },
                "Sales Order Item": {
                    "doctype": "Clearence Item",
                    "field_map": {
                        "parent": "sales_order",
                        "name": "so_detail",
                        "series_number": "series"
                    },
                },
                "Deduction": {
                    "doctype": "Deduction",
                },
                "Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "add_if_empty": True},
            },
            target_doc,
            set_missing_values,
        )

    elif doctype == "Project":
        doclist = get_mapped_doc(
            "Project",
            source_name,
            {
                "Project": {
                    "doctype": "Clearence", 
                    "field_map": {
                        "date": "contract_date",
                        "name": "project",
                    }
                },
                "Project Item": {
                    "doctype": "Clearence Item",
                    "field_map": {
                        "series_number": "series"
                    },
                },
                "Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "add_if_empty": True},
            },
            target_doc,
            set_missing_values,
        )


    new_items, idx = [], 1

    if doctype == "Sales Order":

        c_items = frappe.db.sql(f"""
            select ci.item_code, sum(ci.qty) as qty
            from `tabClearence` as c
            inner join `tabClearence Item` as ci on ci.parent = c.name
            where c.docstatus = 1 and c.sales_order = '{source_name}' and ci.is_group = 0
            group by ci.item_code, ci.parent_group
        """, as_dict = 1)

    elif doctype == "Project":
        c_items = frappe.db.sql(f"""
            select ci.item_code, sum(ci.qty) as qty
            from `tabClearence` as c
            inner join `tabClearence Item` as ci on ci.parent = c.name
            where c.docstatus = 1 and c.project = '{source_name}' and ci.is_group = 0
            group by ci.item_code, ci.parent_group
        """, as_dict = 1)

    new_items = []
    for item in doclist.items:
        toremove = False
        if not item.is_group: 
            for i in c_items:
                if i.item_code == item.item_code and i.qty >= item.qty: 
                    toremove = True
                    break

                elif i.item_code == item.item_code and i.qty < item.qty: 
                    item.qty -= i.qty
                    item.original_qty = item.qty
                    break

        if not toremove: new_items.append(item)

    groups = [g for g in new_items if g.is_group]

    for g in groups:
        found = False
        for item in new_items:
            if not item.is_group and item.parent_group == g.item_code:
                found = True
                break
        if not found:
            new_items.remove(g)

    if not new_items:
        frappe.throw("All Items were Delivered")

    doclist.update({"items": new_items})

    return doclist


@frappe.whitelist()
def create_purchase_clearence(source_name, target_doc=None):

    def set_missing_values(source, target):
        
        if source.project:
            project = frappe.get_doc("Project", source.project)
            target.contract_date = project.date

    doclist = get_mapped_doc(
        "Purchase Order",
        source_name,
        {
            "Purchase Order": {
                "doctype": "Purchase Clearence", 
                "validation": {"docstatus": ["=", 1]},
                "field_map": {
                    "transaction_date": "posting_date",
                    "transaction_date":"purchase_order_date",
                    "name": "purchase_order",
                    "schedule_date": "receipt_date"
                }
            },
            "Purchase Order Item": {
                "doctype": "Purchase Clearence Item",
                "field_map": {
                    "parent": "purchase_order",
                    "name": "po_detail",
                },
            },
            "Deduction": {
				"doctype": "Deduction",
			},
            "Purchase Taxes and Charges": {"doctype": "Purchase Taxes and Charges", "add_if_empty": True},
        },
        target_doc,
        set_missing_values,
    )


    new_items, idx = [], 1

    c_items = frappe.db.sql(f"""
        select ci.item_code, sum(ci.qty) as qty
        from `tabPurchase Clearence` as c
        inner join `tabPurchase Clearence Item` as ci on ci.parent = c.name
        where c.docstatus = 1 and c.purchase_order = '{source_name}'
        group by ci.item_code
    """, as_dict = 1)

    new_items = []
    for item in doclist.items:
        toremove = False
        for i in c_items:
            if i.item_code == item.item_code and i.qty >= item.qty: 
                toremove = True
                break

            elif i.item_code == item.item_code and i.qty < item.qty: 
                item.qty -= i.qty
                break

        if not toremove: new_items.append(item)

    if not new_items:
        frappe.throw("All Items were Receipted")

    doclist.update({"items": new_items})

    return doclist

@frappe.whitelist()
def get_deductions(master_doctype, master_name):
	if not master_name:
		return
	from frappe.model import child_table_fields, default_fields

	deduction_master = frappe.get_doc(master_doctype, master_name)

	deductions = []
	for i, ded in enumerate(deduction_master.get("deductions")):
		ded = ded.as_dict()

		for fieldname in default_fields + child_table_fields:
			if fieldname in ded:
				del ded[fieldname]

		deductions.append(ded)

	return deductions 


@frappe.whitelist()
def get_boq_items(docname, doctype):
    from erpnext.stock.get_item_details import get_conversion_factor

    doc = frappe.get_doc(doctype, docname)

    if doctype == "Sales Order":
        filters = {"sales_order": docname, "docstatus": 1}

    elif doctype == "Project":
        filters = {"project": docname, "docstatus": 1}

    if not frappe.db.exists("Costing Note", filters):
        return

    notes = frappe.db.get_all("Costing Note", filters, "name")

    materials = []
    for note in notes:
        costing_note = frappe.get_doc("Costing Note", note.name)
        for item in costing_note.costing_note_items:
            if item.is_group: continue

            if not frappe.db.exists("BOQ", {"line_id": item.name, "docstatus": 1}): continue


            boq = frappe.get_doc("BOQ", {"line_id": item.name, "docstatus": 1})

            if not boq.get("material_costs"): continue

            for row in boq.material_costs:
                materials.append({
                    "work_pakage": item.parent_group or item.group_item,  ###UPDATE
                    "boq": item.item,
                    "item_code": row.item,
                    "qty": row.qty,
                    "uom": row.uom,
                    "stock_uom": frappe.db.get_value("Item", row.item, "stock_uom"),
                    "conversion_factor": get_conversion_factor(row.item, row.uom).get("conversion_factor", 1),
                    "item_name": frappe.db.get_value("Item", row.item, "item_name"),
                    "rate": row.cost
                })
    return materials


@frappe.whitelist()
def get_items(project, work_package = None, boq = None):
    from erpnext.stock.get_item_details import get_conversion_factor
    if not frappe.db.exists("Costing Note", {"project": project, "docstatus": 1}):
        return

    notes = frappe.db.get_all("Costing Note", {"project": project, "docstatus": 1}, "name")

    materials = []
    for note in notes:
        costing_note = frappe.get_doc("Costing Note", note.name)
        for item in costing_note.costing_note_items:
            if item.is_group: continue
            
            if work_package:
                if item.group_item != work_package: continue

            if boq:
                if item.item != boq: continue

            if not frappe.db.exists("BOQ", {"line_id": item.name, "docstatus": 1}): continue


            boq = frappe.get_doc("BOQ", {"line_id": item.name, "docstatus": 1})

            if not boq.get("material_costs"): continue

            for row in boq.material_costs:
                materials.append({
                    "item_code": row.item,
                    "qty": row.qty,
                    "uom": row.uom or frappe.db.get_value("Item", row.item, "stock_uom"),
                    "stock_uom": frappe.db.get_value("Item", row.item, "stock_uom"),
                    "conversion_factor": get_conversion_factor(row.item, row.uom).get("conversion_factor", 1),
                    "item_name": frappe.db.get_value("Item", row.item, "item_name"),
                    "rate": row.cost
                })
    return materials    
