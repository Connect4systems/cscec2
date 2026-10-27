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


def apply_deductions(deductions, grand_total, conversion_rate=1):
    grand_total = float(grand_total or 0)
    conversion_rate = float(conversion_rate or 0)
    if not math.isfinite(grand_total) or grand_total < 0:
        raise ValueError("Grand total must be a nonnegative finite number")
    if not math.isfinite(conversion_rate) or conversion_rate <= 0:
        raise ValueError("Conversion rate must be a positive finite number")
    total = 0
    for row in deductions:
        percent = float(row.get("percent") or 0)
        if not math.isfinite(percent) or not 0 <= percent <= 100:
            raise ValueError("Deduction percentage must be between zero and 100")
        value = grand_total * percent / 100
        row.set("value", value)
        total += value
    if total > grand_total:
        raise ValueError("Total deductions cannot exceed the grand total")
    return dict(total_deductions=total, base_total_deductions=total*conversion_rate,
        net_payable=grand_total-total)
