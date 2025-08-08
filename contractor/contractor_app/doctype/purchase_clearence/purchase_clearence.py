# Copyright (c) 2024, Jenan Alfahham and contributors
# For license information, please see license.txt

import json
import datetime
from copy import deepcopy

import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint, nowdate, round_based_on_smallest_currency_fraction
from frappe.utils import today  
from frappe.model.mapper import get_mapped_doc
from frappe.contacts.doctype.address.address import get_company_address
from frappe.model.utils import get_fetch_values

from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.accounts.party import get_party_account
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.accounts.doctype.pricing_rule.utils import get_applied_pricing_rules
from erpnext.controllers.accounts_controller import (
	validate_inclusive_tax,
	validate_taxes_and_charges,
)



class PurchaseClearence(Document):
	# def on_submit(self):
	# 	create_a_payment(self)

	# def on_cancel(self):
	# 	self.cancel_payment()

	# def cancel_payment(self):
	# 	"Cancel\Delete the Linked Invoice & Cancel\Delete the Linked Journal Entry"
		
	# 	if not self.purchase_invoice: return

	# 	pi = frappe.get_doc("Purchase Invoice", self.purchase_invoice)

	# 	if pi.docstatus == 0: 
	# 		self.purchase_invoice = None
	# 		pi.delete()

	# 	else:
	# 		if frappe.db.exists("Journal Entry Account", {"reference_name": pi.name, "docstatus": ("!=", 2)}):
	# 			je_name = frappe.db.get_value("Journal Entry Account", {"reference_name": si.name, "docstatus": ("!=", 2)}, "parent")
	# 			je = frappe.get_doc("Journal Entry", je_name)
	# 			if je.docstatus == 0:
	# 				je.delete()

	# 			else: je.cancel()

	# 		pi.cancel()

	# 	if not self.project: return

	# 	project = frappe.get_doc("Project", self.project)

	# 	project.save(ignore_permissions=True)

	def validate(self):
		frappe.flags.round_off_applicable_accounts = []
		if not self.project:
			self.project = frappe.db.get_value("Purchase Order", self.project, "project")
		self.supplier_name = frappe.db.get_value("Supplier", self.supplier, "supplier_name")
		
		self._calculate()
		self.set_qty_as_per_stock_uom()
		self.validate_warehouse()
		self.validate_from_warehouse()
		self.set_supplier_address()
		self.calculate_project_discount_rates()
		self.set_items_qtys()
		self.calculate_amounts()

	def set_items_qtys(self):
		for item in self.items:
			item.original_qty = item.qty

			if not item.total_required_qty and (self.purchase_order or self.project):

				if self.purchase_order:
					qty = frappe.db.sql(
						f"""
						select sum(qty)
						from `tabPurchase Order` as so
						inner join `tabPurchase Order Item` as i on i.parent = so.name
						where so.name = '{self.purchase_order}' and so.docstatus = 1
						and i.item_code = '{item.item_code}'
						group by i.item_code
						""", as_list = 1
					)
					if qty and qty[0]:
						item.total_required_qty = qty[0][0]

						delivered_qty = frappe.db.sql(f"""
							select sum(qty)
							from `tabPurchase Clearence Item` as ci
							inner join `tabPurchase Clearence` as c on c.name = ci.parent
							where c.docstatus = 1 and c.purchase_order = '{self.purchase_order}'
							and ci.item_code = '{item.item_code}'
							group by ci.item_code
						""", as_list = 1)

						if delivered_qty and delivered_qty[0]:
							item.delivered_qty = delivered_qty[0][0]

				elif self.project:
					qty = frappe.db.sql(
						f"""
						select sum(qty)
						from `tabProject` as p
						inner join `tabProject Item` as i on i.parent = p.name
						where p.name = '{self.project}' and i.item_code = '{item.item_code}'
						group by i.item_code
						""", as_list = 1
					)
					if qty and qty[0]:
						item.total_required_qty = qty[0][0]

						delivered_qty = frappe.db.sql(f"""
							select sum(qty)
							from `tabPurchase Clearence Item` as ci
							inner join `tabPurchase Clearence` as c on c.name = ci.parent
							where c.docstatus = 1 and c.project = '{self.project}'
							and ci.item_code = '{item.item_code}'
							group by ci.item_code
						""", as_list = 1)

						if delivered_qty and delivered_qty[0]:
							item.delivered_qty = delivered_qty[0][0]


	def calculate_amounts(self):
		total_amount = frappe.db.sql(f"""
			select sum(current_amount)
			from `tabPurchase Clearence` where purchase_order = '{self.purchase_order}'
			and docstatus = 1
		""", as_list = 1)
		if total_amount and total_amount[0]:
			total_amount = total_amount[0][0]

			self.previous_amount = total_amount

		if not total_amount: 
			total_amount = 0

		if not self.base_total_deductions:
			self.base_total_deductions = 0

		if not self.total_deductions:
			self.total_deductions = 0

		if not self.current_amount:
			self.current_amount = 0

		base_rounded_total = frappe.db.get_value("Purchase Order", self.purchase_order, "base_rounded_total") or 0
		total_without_deductions = base_rounded_total - self.base_total_deductions or 0
		self.due_amount = total_without_deductions - (total_amount + self.current_amount)

	def set_qty_as_per_stock_uom(self):
		for d in self.get("items"):
			if d.meta.get_field("stock_qty"):
				# Check if item code is present
				# Conversion factor should not be mandatory for non itemized items
				if not d.conversion_factor and d.item_code:
					frappe.throw(_("Row {0}: Conversion Factor is mandatory").format(d.idx))
				d.stock_qty = flt(d.qty) * flt(d.conversion_factor)

	def _calculate(self):
		self.calculate_item_values()
		self.initialize_taxes()
		self.calculate_net_total()
		self.calculate_taxes()
		self.manipulate_grand_total_for_inclusive_tax()
		self.calculate_totals()
		self._cleanup()
		self.calculate_total_net_weight()

	def calculate_project_discount_rates(self):
		self.total_deductions = 0
		for d in self.get("deductions"):
			d.value = flt(self.rounded_total * d.percent / 100, self.precision("rounded_total"))
			self.total_deductions += d.value
 
		self.total_after_deductions = self.total_deductions
		self.base_total_deductions = self.total_deductions * self.conversion_rate
		self.current_amount = self.base_rounded_total - self.total_after_deductions
	
	def calculate_item_values(self):
		for item in self.get("items"):
			self.round_floats_in(item)
			if item.discount_percentage == 100:
				item.rate = 0.0
			elif item.price_list_rate:
				if not item.rate or (item.pricing_rules and item.discount_percentage > 0):
					item.rate = flt(
						item.price_list_rate * (1.0 - (item.discount_percentage / 100.0)), item.precision("rate")
					)

					item.discount_amount = item.price_list_rate * (item.discount_percentage / 100.0)

				elif item.discount_amount and item.pricing_rules:
					item.rate = item.price_list_rate - item.discount_amount

			item.rate_with_margin, item.base_rate_with_margin = self.calculate_margin(item)
			if flt(item.rate_with_margin) > 0:
				item.rate = flt(
					item.rate_with_margin * (1.0 - (item.discount_percentage / 100.0)), item.precision("rate")
				)

				if item.discount_amount and not item.discount_percentage:
					item.rate = item.rate_with_margin - item.discount_amount
				else:
					item.discount_amount = item.rate_with_margin - item.rate

			elif flt(item.price_list_rate) > 0:
				item.discount_amount = item.price_list_rate - item.rate
			elif flt(item.price_list_rate) > 0 and not item.discount_amount:
				item.discount_amount = item.price_list_rate - item.rate

			item.net_rate = item.rate

			item.amount = flt(item.rate * item.qty, item.precision("amount"))

			item.net_amount = item.amount

			self._set_in_company_currency(
				item, ["price_list_rate", "rate", "net_rate", "amount", "net_amount"]
			)

			item.item_tax_amount = 0.0

	def _set_in_company_currency(self, doc, fields):
		"""set values in base currency"""
		for f in fields:
			val = flt(
				flt(doc.get(f), doc.precision(f)) * self.conversion_rate, doc.precision("base_" + f)
			)
			doc.set("base_" + f, val)

	def validate_warehouse(self):
		from erpnext.stock.utils import validate_disabled_warehouse, validate_warehouse_company
		
		warehouses = list(set(d.warehouse for d in self.get("items") if getattr(d, "warehouse", None)))

		target_warehouses = list(
			set([d.target_warehouse for d in self.get("items") if getattr(d, "target_warehouse", None)])
		)

		warehouses.extend(target_warehouses)

		from_warehouse = list(
			set([d.from_warehouse for d in self.get("items") if getattr(d, "from_warehouse", None)])
		)

		warehouses.extend(from_warehouse)

		for w in warehouses:
			validate_disabled_warehouse(w)
			validate_warehouse_company(w, self.company)

	def validate_from_warehouse(self):
		for item in self.get("items"):
			if item.get("from_warehouse") and (item.get("from_warehouse") == item.get("warehouse")):
				frappe.throw(
					_("Row #{0}: Accepted Warehouse and Supplier Warehouse cannot be same").format(item.idx)
				)

	def set_supplier_address(self):
		address_dict = {
			"supplier_address": "address_display",
			"shipping_address": "shipping_address_display",
		}

		for address_field, address_display_field in address_dict.items():
			if self.get(address_field):
				self.set(address_display_field, get_address_display(self.get(address_field)))

	
	def calculate_margin(self, item):
		rate_with_margin = 0.0
		base_rate_with_margin = 0.0
		if item.price_list_rate:
			if item.pricing_rules and not self.ignore_pricing_rule:
				has_margin = False
				for d in get_applied_pricing_rules(item.pricing_rules):
					pricing_rule = frappe.get_cached_doc("Pricing Rule", d)

					if pricing_rule.margin_rate_or_amount and (
						(
							pricing_rule.currency == self.currency
							and pricing_rule.margin_type in ["Amount", "Percentage"]
						)
						or pricing_rule.margin_type == "Percentage"
					):
						item.margin_type = pricing_rule.margin_type
						item.margin_rate_or_amount = pricing_rule.margin_rate_or_amount
						has_margin = True

				if not has_margin:
					item.margin_type = None
					item.margin_rate_or_amount = 0.0

			if not item.pricing_rules and flt(item.rate) > flt(item.price_list_rate):
				item.margin_type = "Amount"
				item.margin_rate_or_amount = flt(
					item.rate - item.price_list_rate, item.precision("margin_rate_or_amount")
				)
				item.rate_with_margin = item.rate

			elif item.margin_type and item.margin_rate_or_amount:
				margin_value = (
					item.margin_rate_or_amount
					if item.margin_type == "Amount"
					else flt(item.price_list_rate) * flt(item.margin_rate_or_amount) / 100
				)
				rate_with_margin = flt(item.price_list_rate) + flt(margin_value)
				base_rate_with_margin = flt(rate_with_margin) * flt(self.conversion_rate)

		return rate_with_margin, base_rate_with_margin

	def initialize_taxes(self):
		for tax in self.get("taxes"):
			validate_taxes_and_charges(tax)
			validate_inclusive_tax(tax, self)

			tax.item_wise_tax_detail = {}

			tax_fields = [
				"total",
				"tax_amount_after_discount_amount",
				"tax_amount_for_current_item",
				"grand_total_for_current_item",
				"tax_fraction_for_current_item",
				"grand_total_fraction_for_current_item",
			]

			if tax.charge_type != "Actual":
				tax_fields.append("tax_amount")

			for fieldname in tax_fields:
				tax.set(fieldname, 0.0)

			self.round_floats_in(tax)

	def calculate_net_total(self):
		self.total_qty = (
			self.total
		) = self.base_total = self.net_total = self.base_net_total = 0.0

		for item in self.get("items"):
			self.total += item.amount
			self.total_qty += item.qty
			self.base_total += item.base_amount
			self.net_total += item.net_amount
			self.base_net_total += item.base_net_amount

		self.round_floats_in(self, ["total", "base_total", "net_total", "base_net_total"])

	def calculate_totals(self):
		if self.get("taxes"):
			self.grand_total = flt(self.get("taxes")[-1].total) + flt(self.rounding_adjustment)
		else:
			self.grand_total = flt(self.net_total)

		if self.get("taxes"):
			self.total_taxes_and_charges = flt(
				self.grand_total - self.net_total - flt(self.rounding_adjustment),
				self.precision("total_taxes_and_charges"),
			)
		else:
			self.total_taxes_and_charges = 0.0

		self._set_in_company_currency(self, ["total_taxes_and_charges", "rounding_adjustment"])

	
		self.taxes_and_charges_added = self.taxes_and_charges_deducted = 0.0
		for tax in self.get("taxes"):
			if tax.category in ["Valuation and Total", "Total"]:
				if tax.add_deduct_tax == "Add":
					self.taxes_and_charges_added += flt(tax.tax_amount_after_discount_amount)
				else:
					self.taxes_and_charges_deducted += flt(tax.tax_amount_after_discount_amount)

		#self.round_floats_in(self, ["taxes_and_charges_added", "taxes_and_charges_deducted"])

		self.base_grand_total = (
			flt(self.grand_total * self.conversion_rate)
			if (self.taxes_and_charges_added or self.taxes_and_charges_deducted)
			else self.base_net_total
		)

		# self._set_in_company_currency(
		# 	self, ["taxes_and_charges_added", "taxes_and_charges_deducted"]
		# )
		
		self.round_floats_in(self, ["grand_total", "base_grand_total"])

		self.set_rounded_total()

	def calculate_taxes(self):
		self.rounding_adjustment = 0

		# maintain actual tax rate based on idx
		actual_tax_dict = dict(
			[
				[tax.idx, flt(tax.tax_amount, tax.precision("tax_amount"))]
				for tax in self.get("taxes")
				if tax.charge_type == "Actual"
			]
		)

		for n, item in enumerate(self.get("items")):
			item_tax_map = self._load_item_tax_rate(item.item_tax_rate)
			for i, tax in enumerate(self.get("taxes")):
				# tax_amount represents the amount of tax for the current step
				current_tax_amount = self.get_current_tax_amount(item, tax, item_tax_map)

				# Adjust divisional loss to the last item
				if tax.charge_type == "Actual":
					actual_tax_dict[tax.idx] -= current_tax_amount
					if n == len(self.get("items")) - 1:
						current_tax_amount += actual_tax_dict[tax.idx]

				# accumulate tax amount into tax.tax_amount
				if tax.charge_type != "Actual":
					tax.tax_amount += current_tax_amount

				# store tax_amount for current item as it will be used for
				# charge type = 'On Previous Row Amount'
				tax.tax_amount_for_current_item = current_tax_amount

				# set tax after discount
				tax.tax_amount_after_discount_amount += current_tax_amount

				current_tax_amount = self.get_tax_amount_if_for_valuation_or_deduction(current_tax_amount, tax)

				# note: grand_total_for_current_item contains the contribution of
				# item's amount, previously applied tax and the current tax on that item
				if i == 0:
					tax.grand_total_for_current_item = flt(item.net_amount + current_tax_amount)
				else:
					tax.grand_total_for_current_item = flt(
						self.get("taxes")[i - 1].grand_total_for_current_item + current_tax_amount
					)

				# set precision in the last item iteration
				if n == len(self.get("items")) - 1:
					self.round_off_totals(tax)
					self._set_in_company_currency(tax, ["tax_amount", "tax_amount_after_discount_amount"])

					self.round_off_base_values(tax)
					self.set_cumulative_total(i, tax)

					self._set_in_company_currency(tax, ["total"])

	def round_off_totals(self, tax):
		if tax.account_head in frappe.flags.round_off_applicable_accounts:
			tax.tax_amount = round(tax.tax_amount, 0)
			tax.tax_amount_after_discount_amount = round(tax.tax_amount_after_discount_amount, 0)

		tax.tax_amount = flt(tax.tax_amount, tax.precision("tax_amount"))
		tax.tax_amount_after_discount_amount = flt(
			tax.tax_amount_after_discount_amount, tax.precision("tax_amount")
		)

	def set_cumulative_total(self, row_idx, tax):
		tax_amount = tax.tax_amount_after_discount_amount
		tax_amount = self.get_tax_amount_if_for_valuation_or_deduction(tax_amount, tax)

		if row_idx == 0:
			tax.total = flt(self.net_total + tax_amount, tax.precision("total"))
		else:
			tax.total = flt(self.get("taxes")[row_idx - 1].total + tax_amount, tax.precision("total"))


	def _load_item_tax_rate(self, item_tax_rate):
		return json.loads(item_tax_rate) if item_tax_rate else {}

	def _get_tax_rate(self, tax, item_tax_map):
		if tax.account_head in item_tax_map:
			return flt(item_tax_map.get(tax.account_head), self.precision("rate", tax))
		else:
			return tax.rate

	def get_current_tax_amount(self, item, tax, item_tax_map):
		tax_rate = self._get_tax_rate(tax, item_tax_map)
		current_tax_amount = 0.0

		if tax.charge_type == "Actual":
			# distribute the tax amount proportionally to each item row
			actual = flt(tax.tax_amount, tax.precision("tax_amount"))
			current_tax_amount = (
				item.net_amount * actual / self.net_total if self.net_total else 0.0
			)

		elif tax.charge_type == "On Net Total":
			current_tax_amount = (tax_rate / 100.0) * item.net_amount
		elif tax.charge_type == "On Previous Row Amount":
			current_tax_amount = (tax_rate / 100.0) * self.get("taxes")[
				cint(tax.row_id) - 1
			].tax_amount_for_current_item
		elif tax.charge_type == "On Previous Row Total":
			current_tax_amount = (tax_rate / 100.0) * self.get("taxes")[
				cint(tax.row_id) - 1
			].grand_total_for_current_item
		elif tax.charge_type == "On Item Quantity":
			current_tax_amount = tax_rate * item.qty

		self.set_item_wise_tax(item, tax, tax_rate, current_tax_amount)

		return current_tax_amount

	def set_item_wise_tax(self, item, tax, tax_rate, current_tax_amount):
		# store tax breakup for each item
		key = item.item_code or item.item_name
		item_wise_tax_amount = current_tax_amount * self.conversion_rate
		if tax.item_wise_tax_detail.get(key):
			item_wise_tax_amount += tax.item_wise_tax_detail[key][1]

		tax.item_wise_tax_detail[key] = [tax_rate, flt(item_wise_tax_amount)]

	def get_tax_amount_if_for_valuation_or_deduction(self, tax_amount, tax):
		# if just for valuation, do not add the tax amount in total
		# if tax/charges is for deduction, multiply by -1
		if getattr(tax, "category", None):
			tax_amount = 0.0 if (tax.category == "Valuation") else tax_amount

		return tax_amount

	def round_off_base_values(self, tax):
		# Round off to nearest integer based on regional settings
		if tax.account_head in frappe.flags.round_off_applicable_accounts:
			tax.base_tax_amount = round(tax.base_tax_amount, 0)
			tax.base_tax_amount_after_discount_amount = round(tax.base_tax_amount_after_discount_amount, 0)


	def manipulate_grand_total_for_inclusive_tax(self):
		# if fully inclusive taxes and diff
		if self.get("taxes") and any(cint(t.included_in_print_rate) for t in self.get("taxes")):
			last_tax = self.get("taxes")[-1]
			non_inclusive_tax_amount = sum(
				flt(d.tax_amount_after_discount_amount)
				for d in self.get("taxes")
				if not d.included_in_print_rate
			)

			diff = (
				self.total + non_inclusive_tax_amount - flt(last_tax.total, last_tax.precision("total"))
			)

			diff = flt(diff, self.precision("rounding_adjustment"))

			if diff and abs(diff) <= (5.0 / 10 ** last_tax.precision("tax_amount")):
				self.rounding_adjustment = diff


	def set_rounded_total(self):
		
		if self.meta.get_field("rounded_total"):
			if self.is_rounded_total_disabled():
				self.rounded_total = self.base_rounded_total = 0
				return

			self.rounded_total = round_based_on_smallest_currency_fraction(
				self.grand_total, self.currency, self.precision("rounded_total")
			)

			# if print_in_rate is set, we would have already calculated rounding adjustment
			self.rounding_adjustment += flt(
				self.rounded_total - self.grand_total, self.precision("rounding_adjustment")
			)

			self._set_in_company_currency(self, ["rounding_adjustment", "rounded_total"])


	def calculate_total_net_weight(self):
		self.total_net_weight = 0.0
		for d in self.items:
			if d.total_weight:
				self.total_net_weight += d.total_weight

	def is_rounded_total_disabled(self):
		if self.meta.get_field("disable_rounded_total"):
			return self.disable_rounded_total
		else:
			return frappe.db.get_single_value("Global Defaults", "disable_rounded_total")

	def _cleanup(self):
		for tax in self.get("taxes"):
			if not tax.get("dont_recompute_tax"):
				tax.item_wise_tax_detail = json.dumps(tax.item_wise_tax_detail, separators=(",", ":"))

@frappe.whitelist()
def get_round_off_applicable_accounts(account_list):

	return


@frappe.whitelist()
def make_purchase_invoice(clearence, target_doc=None, ignore_permissions=False):
	def postprocess(source, target):
		target.flags.ignore_permissions = ignore_permissions
		set_missing_values(source, target)
		# Get the advance paid Journal Entries in Purchase Invoice Advance
		if target.get("allocate_advances_automatically"):
			target.set_advances()

		target.set_payment_schedule()
		target.credit_to = get_party_account("Supplier", source.supplier, source.company)


	def set_missing_values(source, target):
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(obj, target, source_parent):
		target.amount = flt(obj.amount) - flt(obj.billed_amt)
		target.base_amount = target.amount * flt(source_parent.conversion_rate)
		target.qty = (
			target.amount / flt(obj.rate) if (flt(obj.rate) and flt(obj.billed_amt)) else flt(obj.qty)
		)

		item = get_item_defaults(target.item_code, source_parent.company)
		item_group = get_item_group_defaults(target.item_code, source_parent.company)
		target.cost_center = (
			obj.cost_center
			or frappe.db.get_value("Project", obj.project, "cost_center")
			or item.get("buying_cost_center")
			or item_group.get("buying_cost_center")
		)

	clearence = frappe.get_doc("Purchase Clearence", clearence)
	source_name = clearence.purchase_order
	doclist = get_mapped_doc(
		"Purchase Order",
		source_name,
		{
			"Purchase Order": {
				"doctype": "Purchase Invoice",
				"field_map": {
					"party_account_currency": "party_account_currency",
					"supplier_warehouse": "supplier_warehouse",
				},
				"field_no_map": ["payment_terms_template"],
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Purchase Order Item": {
				"doctype": "Purchase Invoice Item",
				"field_map": {
					"name": "po_detail",
					"parent": "purchase_order",
				},
				"postprocess": update_item,
				"condition": lambda doc: doc.qty
				and (doc.base_amount == 0 or abs(doc.billed_amt) < abs(doc.amount)),
			},
			"Purchase Taxes and Charges": {"doctype": "Purchase Taxes and Charges", "add_if_empty": True},
		},
		target_doc,
		postprocess,
		ignore_permissions=ignore_permissions,
	)
	doclist.clearence = clearence.name
	doclist.update({"deductions": clearence.deductions})
	newitems = []
	for source in doclist.items:
		found = False
		for item in clearence.items:

			if source.item_code == item.item_code:
				source.qty = item.qty
				source.rate = item.rate
				found = True
				break

		if found:
			newitems.append(source)

	doclist.update({"items": newitems})

	automatically_fetch_payment_terms = cint(
		frappe.db.get_single_value("Accounts Settings", "automatically_fetch_payment_terms")
	)
	if automatically_fetch_payment_terms:
		doclist.set_payment_schedule()

	doclist.set_onload("ignore_price_list", True)

	return doclist


def make_purchase_receipt(clearence, purchase_invoice):
	from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import make_purchase_receipt

	doc = make_purchase_receipt(purchase_invoice)
	
	boqs = frappe.db.sql(f"""
		select distinct boq.name, boq.item, cni.group_item, 
		m.item as m_item, m.qty as m_qty, m.cost as m_rate, m.total_cost as m_amount
		from `tabCosting Note` as cn
		inner join `tabCosting Note Items` cni on cn.name = cni.parent
		inner join `tabBOQ` as boq on boq.costing_note = cn.name and boq.line_id = cni.name
		inner join `tabMaterial costs` as m on m.parent = boq.name
		where cn.docstatus = 1 and boq.docstatus = 1 and cn.purchase_order = '{clearence.purchase_order}'
	""", as_dict = 1)

	if not boqs: return
	
	items = deepcopy(doc.items)
	for item in items:
		if frappe.db.get_value("Item", item.item_code, "is_group"): continue

		group_item = frappe.db.get_value("Purchase Order Item", {
			"parent": clearence.purchase_order, 
			"docstatus": 1,
			"name": item.so_detail
		}, "group_item")

		for i in boqs:
			if i.item == item.item_code and i.group_item == group_item:
				doc.append("items", {
					"item_code": i.m_item,
					"item_name": frappe.db.get_value("Item", i.m_item, "item_name"),
					"uom": frappe.db.get_value("Item", i.m_item, "stock_uom"),
					"qty": i.m_qty,
					"rate": i.m_rate,
					"amount": i.m_amount,
					# "against_purchase_order": clearence.purchase_order,
					# "against_purchase_invoice": item.against_purchase_invoice
				})


	return doc

@frappe.whitelist()	
def create_a_payment(source_name, target_doc = None):
	purchase_invoice = frappe.get_doc("Purchase Invoice", source_name)
	total_after_deductions = frappe.db.get_value("Purchase Clearence", purchase_invoice.clearence, "total_after_deductions")

	je = frappe.new_doc("Journal Entry")
	je.posting_date = nowdate()
	accounts = []

	creditors = frappe.db.get_value("Company", purchase_invoice.company, "default_payable_account")

	if not creditors:
		return

	accounts.append(frappe._dict(
		{
			"account": creditors,
			"party_type": "Supplier",
			"party": purchase_invoice.supplier,
			"debit_in_account_currency": flt(total_after_deductions, 3),
			"reference_type": "Purchase Invoice",
			"reference_name": purchase_invoice.name
		}
	))
	for ded in purchase_invoice.deductions:
		accounts.append(frappe._dict(
			{
				"account": ded.account,
				"credit_in_account_currency": flt(ded.value, 3),
			}
		))


	je.update({"accounts": accounts})
	
	return je
