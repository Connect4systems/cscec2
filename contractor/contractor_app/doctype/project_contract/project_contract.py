import frappe
from frappe.model.document import Document
from frappe.utils import getdate, flt

from contractor.project_contract import require_ready
from contractor.project_contract_rules import contract_totals
from contractor.tender_logic import number_rows


class ProjectContract(Document):
    def validate(self):
        # Serialize competing saves; a tender has at most one active contract.
        frappe.db.sql("select name from `tabTender Analysis` where name=%s for update", self.tender_analysis)
        tender = frappe.get_doc("Tender Analysis", self.tender_analysis)
        tender.check_permission("read")
        require_ready(tender)
        duplicate = frappe.db.get_value("Project Contract", {"tender_analysis": tender.name,
            "docstatus": ["<", 2], "name": ["!=", self.name or ""]}, "name")
        if duplicate:
            frappe.throw(f"Tender already has an active Project Contract: {duplicate}")
        if self.company != tender.company or self.currency != tender.currency:
            frappe.throw("Company and currency must match the Tender Analysis")
        if tender.party_type == "Customer" and self.customer != tender.party_name:
            frappe.throw("Customer must match the Tender Analysis")
        if getdate(self.delivery_date) < getdate(self.transaction_date):
            frappe.throw("Delivery date cannot be before the contract date")
        if frappe.get_cached_value("Company", self.company, "default_currency") == self.currency:
            self.conversion_rate = 1
        if len(self.clauses) != len(tender.clauses):
            frappe.throw("Project Contract must include every tender clause")
        for row, source in zip(self.clauses, tender.clauses):
            if (row.source_row != source.name or row.contractual_clause != source.contractual_clause
                    or bool(row.is_group) != bool(source.is_group)):
                frappe.throw(f"Row {row.idx}: clause does not match the Tender Analysis")
            row.clause_title = source.clause_title
            row.series_number = source.series_number
            row.costing_note = source.applied_costing_note
            if row.submitted_boq:
                boq = frappe.db.get_value("BOQ", row.submitted_boq,
                    ["tender_analysis", "contractual_clause", "docstatus", "costing_note"], as_dict=True)
                if (not boq or boq.docstatus != 1 or boq.tender_analysis != tender.name
                        or boq.contractual_clause != source.contractual_clause
                        or boq.costing_note != source.applied_costing_note):
                    frappe.throw(f"Row {row.idx}: BOQ must be submitted and match the priced clause")
            if not row.is_group:
                row.delivery_date = row.delivery_date or self.delivery_date
                if getdate(row.delivery_date) < getdate(self.transaction_date):
                    frappe.throw(f"Row {row.idx}: delivery date is before the contract date")
        for row in list(self.taxes) + list(self.deductions):
            account = row.get("account_head") or row.get("account")
            if account and frappe.get_cached_value("Account", account, "company") != self.company:
                frappe.throw("Tax and deduction accounts must belong to the contract company")
        for name in ("advance_payment_discount", "business_guarantee_insurance_deduction_rate"):
            if not 0 <= flt(self.get(name)) <= 100:
                frappe.throw("Contracting percentages must be between zero and 100")
        try:
            number_rows(self.clauses, "From Excel")
            self.update(contract_totals(self.clauses, self.taxes, self.deductions,
                self.discount_amount, self.conversion_rate))
        except ValueError as exc:
            frappe.throw(str(exc))
        self.contractor_order = 1
        self.tender_number = tender.tender_number
        self.status = "Submitted" if self.docstatus == 1 else "Draft"

    def on_cancel(self):
        self.db_set("status", "Cancelled", update_modified=False)
