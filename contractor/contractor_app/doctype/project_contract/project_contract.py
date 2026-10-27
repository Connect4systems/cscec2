import frappe
from frappe.model.document import Document
from frappe.utils import getdate, flt

from contractor.project_contract import require_ready
from contractor.project_contract_taxes import calculate_contract_taxes, get_sales_tax_template, validate_template
from contractor.tender_logic import number_rows


class ProjectContract(Document):
    def validate(self):
        # A tender has at most one active document of each commercial type.
        frappe.db.sql("select name from `tabTender Analysis` where name=%s for update", self.tender_analysis)
        tender = frappe.get_doc("Tender Analysis", self.tender_analysis)
        tender.check_permission("read")
        require_ready(tender)
        duplicate = frappe.db.get_value(self.doctype, {"tender_analysis": tender.name,
            "docstatus": ["<", 2], "name": ["!=", self.name or ""]}, "name")
        if duplicate:
            frappe.throw(f"Tender already has an active {self.doctype}: {duplicate}")
        offer = None
        if self.doctype == "Project Contract" and self.get("project_offer"):
            from contractor.project_offer import validate_offer_source
            offer = validate_offer_source(self)
        if self.company != tender.company or self.currency != tender.currency:
            frappe.throw("Company and currency must match the Tender Analysis")
        if tender.party_type == "Customer" and self.customer != tender.party_name:
            frappe.throw("Customer must match the Tender Analysis")
        if getdate(self.delivery_date) < getdate(self.transaction_date):
            frappe.throw("Delivery date cannot be before the contract date")
        if frappe.get_cached_value("Company", self.company, "default_currency") == self.currency:
            self.conversion_rate = 1
        source_clauses = offer.clauses if offer else tender.clauses
        if len(self.clauses) != len(source_clauses):
            frappe.throw(f"{self.doctype} must include every source clause")
        for row, source in zip(self.clauses, source_clauses):
            source_id = source.source_row if offer else source.name
            source_note = source.costing_note if offer else source.applied_costing_note
            if (row.source_row != source_id or row.contractual_clause != source.contractual_clause
                    or bool(row.is_group) != bool(source.is_group)):
                frappe.throw(f"Row {row.idx}: clause does not match the Tender Analysis")
            row.clause_title = source.clause_title
            row.series_number = source.series_number
            row.costing_note = source_note
            if row.submitted_boq:
                boq = frappe.db.get_value("BOQ", row.submitted_boq,
                    ["tender_analysis", "contractual_clause", "docstatus", "costing_note"], as_dict=True)
                if (not boq or boq.docstatus != 1 or boq.tender_analysis != tender.name
                        or boq.contractual_clause != source.contractual_clause
                        or boq.costing_note != source_note):
                    frappe.throw(f"Row {row.idx}: BOQ must be submitted and match the priced clause")
            if not row.is_group:
                row.delivery_date = row.delivery_date or self.delivery_date
                if getdate(row.delivery_date) < getdate(self.transaction_date):
                    frappe.throw(f"Row {row.idx}: delivery date is before the contract date")
        for row in list(self.taxes) + list(self.deductions):
            account = row.get("account_head") or row.get("account")
            if account and frappe.get_cached_value("Account", account, "company") != self.company:
                frappe.throw("Tax and deduction accounts must belong to the contract company")
        if self.get("taxes_and_charges"):
            validate_template(self.taxes_and_charges, self.company)
            old = self.get_doc_before_save()
            if (self.is_new() or not old or old.get("taxes_and_charges") != self.taxes_and_charges) and not self.taxes:
                self.set("taxes", get_sales_tax_template(self.taxes_and_charges, self.company))
        try:
            number_rows(self.clauses, "From Excel")
        except ValueError as exc:
            frappe.throw(str(exc))
        calculate_contract_taxes(self)
        self.contractor_order = 1
        self.tender_number = tender.tender_number
        self.status = "Submitted" if self.docstatus == 1 else "Draft"

    def on_cancel(self):
        self.db_set("status", "Cancelled", update_modified=False)
