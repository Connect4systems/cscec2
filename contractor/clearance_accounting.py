"""One service invoice plus its deduction settlement; no duplicate revenue journal."""
import frappe
from frappe.utils import flt


WORK_ITEM = "بنود اعمال"


def work_item():
    existing = WORK_ITEM if frappe.db.exists("Item", WORK_ITEM) else frappe.db.get_value("Item", {"item_name": WORK_ITEM}, "name")
    if existing:
        item = frappe.get_doc("Item", existing)
        if item.is_stock_item or item.disabled or not item.is_sales_item or not item.is_purchase_item:
            frappe.throw("Item بنود اعمال must be enabled, non-stock, and usable for sales and purchases")
        return item
    if not frappe.db.exists("UOM", "Nos"):
        frappe.throw("Create UOM Nos before posting a certificate")
    group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
    if not group:
        frappe.throw("Create a leaf Item Group before posting a certificate")
    return frappe.get_doc(dict(doctype="Item", item_code=WORK_ITEM, item_name=WORK_ITEM,
        is_stock_item=0, is_sales_item=1, is_purchase_item=1, stock_uom="Nos", item_group=group)).insert()


def deduction_lines(doc, party_account, base_currency, cost_center):
    """Produce a balanced base-currency settlement, respecting account currencies."""
    buying = doc.doctype == "Subcontract Clearnce"
    party_type, party = ("Supplier", doc.supplier) if buying else ("Customer", doc.customer)
    precision = doc.precision("base_total_deductions") or 2
    rows = []
    for deduction in doc.deductions:
        if not flt(deduction.value):
            continue
        if deduction.account == party_account:
            frappe.throw("A deduction account cannot be the invoice's party account")
        currency = frappe.get_cached_value("Account", deduction.account, "account_currency") or base_currency
        if currency not in (base_currency, doc.currency):
            frappe.throw("Deduction accounts must use the company or certificate currency")
        rate = 1 if currency == base_currency else doc.conversion_rate
        amount = flt(deduction.value * doc.conversion_rate, precision) if currency == base_currency else deduction.value
        values = dict(account=deduction.account, account_currency=currency, exchange_rate=rate, cost_center=cost_center)
        values["credit_in_account_currency" if buying else "debit_in_account_currency"] = amount
        values["credit" if buying else "debit"] = flt(amount*rate, precision)
        if frappe.get_cached_value("Account", deduction.account, "account_type") in ("Receivable", "Payable"):
            values.update(party_type=party_type, party=party)
        rows.append(values)
    currency = frappe.get_cached_value("Account", party_account, "account_currency") or base_currency
    if currency not in (base_currency, doc.currency):
        frappe.throw("Party account must use the company or certificate currency")
    rate = 1 if currency == base_currency else doc.conversion_rate
    amount = flt(doc.total_deductions*doc.conversion_rate, precision) if currency == base_currency else doc.total_deductions
    values = dict(account=party_account, account_currency=currency, exchange_rate=rate,
        party_type=party_type, party=party, reference_type=doc.invoice_doctype, reference_name=doc.invoice)
    values["debit_in_account_currency" if buying else "credit_in_account_currency"] = amount
    values["debit" if buying else "credit"] = flt(amount*rate, precision)
    rows.append(values)
    difference = flt(sum(row.get("debit", 0)-row.get("credit", 0) for row in rows), precision)
    if difference:
        account = frappe.get_cached_value("Company", doc.company, "round_off_account")
        if not account:
            frappe.throw("Set the Company Round Off Account to settle currency rounding differences")
        rounding = dict(account=account, account_currency=base_currency, exchange_rate=1, cost_center=cost_center)
        rounding["credit_in_account_currency" if difference > 0 else "debit_in_account_currency"] = abs(difference)
        rounding["credit" if difference > 0 else "debit"] = abs(difference)
        rows.append(rounding)
    return rows


def post_accounting(doc):
    buying = doc.doctype == "Subcontract Clearnce"
    invoice_type = "Purchase Invoice" if buying else "Sales Invoice"
    party_type, party = ("Supplier", doc.supplier) if buying else ("Customer", doc.customer)
    from erpnext.accounts.party import get_party_account
    party_account = get_party_account(party_type, party, doc.company)
    if not party_account:
        frappe.throw("Configure the company's party account before submitting the certificate")
    cost_center = doc.get("cost_center") or frappe.get_cached_value("Project", doc.project, "cost_center") or frappe.get_cached_value("Company", doc.company, "cost_center")
    if not doc.get("invoice"):
        item = work_item()
        account = frappe.get_cached_value("Company", doc.company, "default_expense_account" if buying else "default_income_account")
        if not account or not cost_center:
            frappe.throw("Configure the company default income/expense account and Cost Center")
        invoice = frappe.new_doc(invoice_type)
        invoice.update(dict(company=doc.company, currency=doc.currency, conversion_rate=doc.conversion_rate,
            posting_date=doc.posting_date, due_date=doc.posting_date, update_stock=0,
            disable_rounded_total=1, ignore_pricing_rule=1, contractor_order=0,
            additional_discount_percentage=0, discount_amount=0, apply_discount_on="Net Total",
            remarks=f"{doc.doctype}: {doc.name}"))
        invoice.set("supplier" if buying else "customer", party)
        invoice.set("credit_to" if buying else "debit_to", party_account)
        values = dict(item_code=item.name, item_name=WORK_ITEM, description=f"{WORK_ITEM} — {doc.doctype} {doc.name}",
            qty=1, rate=doc.net_total, uom=item.stock_uom, conversion_factor=1,
            project=doc.project, cost_center=cost_center)
        values["expense_account" if buying else "income_account"] = account
        invoice.append("items", values)
        from contractor.project_contract_taxes import tax_values
        for tax in doc.taxes:
            values = tax_values(tax)
            amount = tax.get("tax_amount_after_discount_amount")
            values.update(charge_type="Actual", row_id=None, rate=0, included_in_print_rate=0,
                tax_amount=tax.tax_amount if amount is None else amount)
            invoice.append("taxes", values)
        invoice.insert()
        if abs(flt(invoice.grand_total)-flt(doc.grand_total)) > 10**-(doc.precision("grand_total") or 2):
            frappe.throw("Invoice total differs from the certificate; accounting was not posted")
        invoice.submit()
        doc.db_set("invoice_doctype", invoice_type, update_modified=False)
        doc.db_set("invoice", invoice.name, update_modified=False)
    else:
        invoice = frappe.get_doc(invoice_type, doc.invoice)
        if (invoice.docstatus != 1 or invoice.company != doc.company or invoice.currency != doc.currency
                or invoice.get("supplier" if buying else "customer") != party
                or abs(flt(invoice.grand_total)-flt(doc.grand_total)) > 0.01):
            frappe.throw("The linked certificate invoice must be submitted and belong to this company")
    if doc.total_deductions and not doc.get("deduction_entry"):
        base = frappe.get_cached_value("Company", doc.company, "default_currency")
        rows = deduction_lines(doc, party_account, base, cost_center)
        entry = frappe.new_doc("Journal Entry")
        entry.update(dict(voucher_type="Journal Entry", company=doc.company, posting_date=doc.posting_date,
            user_remark=f"Deductions — {doc.doctype}: {doc.name}",
            multi_currency=int(any(row["account_currency"] != base for row in rows))))
        for row in rows:
            entry.append("accounts", row)
        entry.insert()
        entry.submit()
        doc.db_set("deduction_entry", entry.name, update_modified=False)


def cancel_accounting(doc):
    # Native cancellation checks reject paid/otherwise dependent invoices; the
    # enclosing transaction restores everything if any reversal cannot complete.
    for doctype, name in (("Journal Entry", doc.get("deduction_entry")), (doc.get("invoice_doctype"), doc.get("invoice"))):
        if name:
            linked = frappe.get_doc(doctype, name)
            if linked.docstatus == 1:
                linked.cancel()
