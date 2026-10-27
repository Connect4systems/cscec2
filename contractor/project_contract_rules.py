"""Readiness and commercial totals for clause-based project contracts."""
import math


def require_submitted_costing(clauses, notes):
    if not notes or any(note.get("docstatus") != 1 for note in notes):
        raise ValueError("Submit all active Costing Notes before creating a Project Contract")
    submitted = {note.get("name") for note in notes}
    details = [row for row in clauses if not row.get("is_group")]
    if not details:
        raise ValueError("The tender must contain at least one detail clause")
    for row in details:
        if not row.get("contractual_clause") or row.get("applied_costing_note") not in submitted:
            raise ValueError("Every detail clause must have pricing applied by a submitted Costing Note")


def contract_totals(clauses, taxes, deductions, discount=0, conversion_rate=1):
    def numeric(value, label, positive=False):
        result = float(value or 0)
        if not math.isfinite(result) or result < 0 or (positive and result == 0):
            raise ValueError(f"{label} must be a valid {'positive' if positive else 'nonnegative'} number")
        return result

    conversion_rate = numeric(conversion_rate, "Conversion rate", True)
    total = total_qty = 0
    group = None
    for row in clauses:
        if row.get("is_group"):
            group = row
            row.set("rate", 0)
            row.set("amount", 0)
            continue
        qty = numeric(row.get("qty"), "Clause quantity", True)
        rate = numeric(row.get("rate"), "Clause rate")
        amount = qty * rate
        row.set("amount", amount)
        if group is not None:
            group.set("amount", group.get("amount") + amount)
        total += amount
        total_qty += qty
    discount = numeric(discount, "Discount")
    if discount > total:
        raise ValueError("Discount cannot exceed the clause total")
    net = total - discount
    total_taxes = 0
    for row in taxes:
        if row.get("charge_type") == "Actual":
            amount = numeric(row.get("tax_amount"), "Tax amount")
        elif row.get("charge_type") == "On Net Total":
            amount = net * numeric(row.get("rate"), "Tax rate") / 100
        else:
            raise ValueError("Select Actual or On Net Total for each tax row")
        row.set("tax_amount", amount)
        row.set("base_tax_amount", amount * conversion_rate)
        total_taxes += amount
    grand = net + total_taxes
    total_deductions = 0
    for row in deductions:
        percent = numeric(row.get("percent"), "Deduction percentage")
        if percent > 100:
            raise ValueError("Deduction percentage cannot exceed 100")
        value = grand * percent / 100
        row.set("value", value)
        total_deductions += value
    if total_deductions > grand:
        raise ValueError("Total deductions cannot exceed the grand total")
    return dict(total_qty=total_qty, total=total, net_total=net,
        total_taxes_and_charges=total_taxes, grand_total=grand,
        total_deductions=total_deductions, net_payable=grand-total_deductions,
        base_total=total*conversion_rate, base_grand_total=grand*conversion_rate,
        base_total_deductions=total_deductions*conversion_rate)
