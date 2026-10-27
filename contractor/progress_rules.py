"""Quantity rules for contract clauses and period-based certificates."""
import math


PROJECT_FIELDS = ("is_group", "series_number", "clause_title", "contractual_clause", "qty", "uom",
    "parent_series", "source_row", "costing_note", "submitted_boq", "delivery_date", "contract_clause_row")


def project_clause_values(row):
    return {field: row.get(field) for field in PROJECT_FIELDS if row.get(field) is not None}


def quantity(value):
    value = float(value or 0)
    if not math.isfinite(value) or value < 0:
        raise ValueError("Quantities must be finite, nonnegative numbers")
    return value


def certificate_quantity(total, previous, current):
    total, previous, current = quantity(total), quantity(previous), quantity(current)
    if previous + current > total + 0.000001:
        raise ValueError("Current quantity exceeds the remaining contract quantity")
    return max(0, total-previous-current)


def update_quantities(rows, customer, subcontract):
    summaries = {}
    group = None
    for row in rows:
        if row.get("is_group"):
            group = row
            for field in ("completed_qty", "remaining_qty", "completion_percentage", "subcontract_completed_qty",
                    "subcontract_remaining_qty", "subcontract_completion_percentage"):
                row.set(field, 0)
            continue
        total = quantity(row.get("qty"))
        done = quantity(customer.get(row.get("name"), 0))
        sub = quantity(subcontract.get(row.get("name"), 0))
        row.set("completed_qty", done)
        row.set("remaining_qty", max(0, total-done))
        row.set("completion_percentage", done/total*100 if total else 0)
        row.set("subcontract_completed_qty", sub)
        row.set("subcontract_remaining_qty", max(0, total-sub))
        row.set("subcontract_completion_percentage", sub/total*100 if total else 0)
        group_series = group.get("series_number") if group else row.get("parent_series") or ""
        # Different units never share a quantity total.
        key = (group.get("name") if group else group_series, row.get("uom") or "")
        if key not in summaries:
            summaries[key] = dict(group_series=group_series, group_title=group.get("clause_title") if group else "Ungrouped",
                uom=row.get("uom"), qty=0, completed_qty=0, subcontract_completed_qty=0)
        summary = summaries[key]
        summary["qty"] += total
        summary["completed_qty"] += done
        summary["subcontract_completed_qty"] += sub
    for summary in summaries.values():
        total = summary["qty"]
        summary["remaining_qty"] = max(0, total-summary["completed_qty"])
        summary["completion_percentage"] = summary["completed_qty"]/total*100 if total else 0
        summary["subcontract_remaining_qty"] = max(0, total-summary["subcontract_completed_qty"])
        summary["subcontract_completion_percentage"] = summary["subcontract_completed_qty"]/total*100 if total else 0
    return list(summaries.values())
