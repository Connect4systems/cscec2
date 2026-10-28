# Copyright (c) 2024, Jenan Alfahham and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class BOQ(Document):
	def validate(self):
		from contractor.project_names import fill_project_name
		fill_project_name(self)
		if self.get("contractual_clause"):
			self.clause_title = frappe.db.get_value("Contractual Clause", self.contractual_clause, "title")
		from contractor.boq_quantities import calculate_resources
		old = self.get_doc_before_save()
		convert_legacy = self.is_new() or self.docstatus == 0 or (old and old.docstatus == 0)
		if self.get("tender_analysis"):
			note = frappe.get_doc("Costing Note", self.costing_note)
			note.check_permission("read")
			source = next((row for row in note.costing_note_items if row.name == self.line_id), None)
			if not source or source.is_group or source.contractual_clause != self.contractual_clause:
				frappe.throw("BOQ clause does not match its Costing Note row")
			self.project_qty = source.qty
		try:
			calculate_resources(self, convert_legacy=convert_legacy)
		except ValueError as exc:
			frappe.throw(str(exc))

	def on_update(self):
		if self.get("tender_analysis"):
			from contractor.tender_pricing import sync_boq_reference
			sync_boq_reference(self)

	def on_submit(self):
		if self.tender_analysis:
			from contractor.tender_pricing import update_from_boq, sync_tender_boq_links
			update_from_boq(self)
			sync_tender_boq_links(self.tender_analysis)
			return

		if not self.costing_note or not self.line_id:
			frappe.throw("The BOQ has no Costing Note as a Reference")

		doc = frappe.get_doc("Costing Note", self.costing_note)
		for row in doc.costing_note_items:
			if row.name == self.line_id:
				row.item = self.item
				row.cost = self.unit_cost
				row.total_cost = self.project_total_cost
				break

		doc.save(ignore_permissions = True)

	def on_cancel(self):
		if self.tender_analysis:
			from contractor.tender_pricing import update_from_boq, sync_boq_reference, sync_tender_boq_links
			update_from_boq(self, cancel=True)
			sync_boq_reference(self, remove=True)
			sync_tender_boq_links(self.tender_analysis)
			return

		doc = frappe.get_doc("Costing Note", self.costing_note)
		for row in doc.costing_note_items:
			if row.name == self.line_id:
				row.cost = 0
				row.total_cost = 0
				row.target_selling_price = 0

				break

		doc.save(ignore_permissions = True)


@frappe.whitelist()
def set_boq_template(boq_template):

	if not frappe.db.exists("Template BOQ", boq_template): return

	tables = {}

	temp = frappe.get_doc("Template BOQ", boq_template)

	for table in ["material_costs", "labor_costs", "contractors_table", "expenses_table"]:
		if temp.get(table):

			tables[table] = []

			for row in temp.get(table):
				item = frappe._dict({
					"cost": row.get("cost", 0),
					"qty": row.get("qty", 0),
					"per_unit_qty": row.get("qty", 0),
					"uom": row.get("uom"),
					"item": row.item,
					"total_cost": row.get("total_cost", 0)
				})
				if table == "material_costs": item["depreciasion_percentage"] = row.get("depreciasion_percentage")
				else: item["uom"] = row.uom

				tables[table].append(item)

	return tables

