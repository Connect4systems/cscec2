# Copyright (c) 2024, Jenan Alfahham and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CostingNote(Document):
	def before_cancel(self):
		if self.get("tender_analysis"):
			# Submitted BOQs remain an audit trail; cancel them after the note.
			self.ignore_linked_doctypes = ["BOQ"]

	def validate(self):
		from contractor.project_names import fill_project_name
		fill_project_name(self)
		if self.get("sales_order"):
			if self.is_new():
				frappe.throw("Create a Project Contract from Tender Analysis instead")
			return
		if self.get("opportunity") and not self.is_new():
			return
		if self.get("opportunity"):
			frappe.throw("Create tender pricing from Tender Analysis")
		if self.get("tender_analysis"):
			from contractor.tender_pricing import validate_note
			validate_note(self)
		else:
			self.update_prices_and_costs()

	def on_submit(self):
		if self.get("tender_analysis"):
			from contractor.tender_pricing import apply_note
			apply_note(self)
		else:
			self.update_linked_doc()

	def on_cancel(self):
		if self.get("tender_analysis"):
			from contractor.tender_pricing import apply_note
			apply_note(self, cancel=True)

		elif self.get("purchase_order"):
			doc = frappe.get_doc("Purchase Order", self.purchase_order)
			for row in self.costing_note_items:
				for item in doc.items:
					if item.item_code == row.item and (item.group_item == row.group_item or (not row.group_item and not item.group_item)):
						if item.rate <= row.target_selling_price:
							item.rate -= row.target_selling_price
						else: item.rate = 0
						break
			doc.save(ignore_permissions=True)

		elif self.get("source_project"):
			doc = frappe.get_doc("Project", self.source_project)
			for row in self.costing_note_items:
				for item in doc.items:
					if item.item_code == row.item and (item.group_item == row.group_item or (not row.group_item and not item.group_item)):
						if item.rate <= row.target_selling_price:
							item.rate -= row.target_selling_price
						else: item.rate = 0
						break
			doc.save(ignore_permissions=True)


	def update_prices_and_costs(self):
		total_cost, total_amount, total_profit = 0, 0, 0
		for row in self.costing_note_items:
			row.total_cost = row.get("cost", 0) * row.qty
			row.target_selling_price = row.get("total_cost", 0) + (row.get("total_cost", 0) * row.get("default_profit_margin", 0) / 100)
			total_cost += row.total_cost
			total_amount += row.target_selling_price
			total_profit += row.target_selling_price - row.total_cost

		self.total_cost = total_cost
		self.total_target_selling_price = total_amount
		self.total_profit = total_profit
		self.profit_margin = self.total_profit / self.total_cost * 100 if self.total_cost else 0


	def update_linked_doc(self):

		if self.get("purchase_order"):
			po = frappe.get_doc("Purchase Order", self.purchase_order)

			for row in self.costing_note_items:
				if row.item == "Unknown" or row.item == "Unknown Group":
					frappe.throw("Row {}: No Correct Item Code is Set".format(row.idx))

				for item in po.items:
					if item.item_code == row.item and item.group_item == row.group_item or (not row.group_item and not item.group_item):
						item.rate = row.target_selling_price / row.qty
						item.amount = row.target_selling_price
						break
			
			po.save(ignore_permissions=True)

		elif self.get("source_project"):
			po = frappe.get_doc("Project", self.source_project)

			for row in self.costing_note_items:
				if row.item == "Unknown" or row.item == "Unknown Group":
					frappe.throw("Row {}: No Correct Item Code is Set".format(row.idx))

				for item in po.items:
					if item.item_code == row.item and item.group_item == row.group_item or (not row.group_item and not item.group_item):
						item.rate = row.target_selling_price / row.qty
						item.amount = row.target_selling_price
						break
			
			po.save(ignore_permissions=True)

