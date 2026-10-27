"""Tender numbering and pricing rules, independent of the Frappe runtime."""
import math
import re


def _set_value(row, field, value):
    """Excel rows are dictionaries; Frappe child documents expose set()."""
    if isinstance(row, dict):
        row[field] = value
    else:
        row.set(field, value)


def number_rows(rows, mode="Automatic"):
    group = sub = 0
    parent = None
    seen = set()
    for index, row in enumerate(rows, 1):
        if not str(row.get("clause_title") or "").strip():
            raise ValueError(f"Row {index}: Contractual Clause Title is required")
        if row.get("is_group"):
            group += 1
            sub = 0
            expected = str(group)
        else:
            if parent is None:
                raise ValueError(f"Row {index}: add a group before detail clauses")
            sub += 1
            expected = f"{group}_{sub}"
        series = str(row.get("series_number") or "").strip() if mode == "From Excel" else expected
        pattern = r"[1-9]\d*" if row.get("is_group") else r"[1-9]\d*_[1-9]\d*"
        if not re.fullmatch(pattern, series) or series in seen:
            raise ValueError(f"Row {index}: invalid or duplicate series {series!r}")
        if not row.get("is_group") and series.split("_")[0] != parent:
            raise ValueError(f"Row {index}: series must belong to preceding group {parent}")
        _set_value(row, "series_number", series)
        _set_value(row, "parent_series", "" if row.get("is_group") else parent)
        seen.add(series)
        if row.get("is_group"):
            parent = series
        else:
            qty = float(row.get("qty") or 0)
            if not math.isfinite(qty) or qty <= 0:
                raise ValueError(f"Row {index}: detail quantity must be greater than zero")
    return rows


def price_rows(rows):
    total_cost = total_selling = 0
    group = None
    for row in rows:
        if row.get("is_group"):
            group = row
            _set_value(row, "total_cost", 0)
            _set_value(row, "target_selling_price", 0)
            _set_value(row, "cost", 0)
            continue
        qty = float(row.get("qty") or 0)
        if not math.isfinite(qty) or qty <= 0:
            raise ValueError("Detail quantity must be greater than zero")
        unit_cost = float(row.get("cost") or 0)
        margin = float(row.get("default_profit_margin") or 0)
        if not math.isfinite(unit_cost) or unit_cost < 0 or not math.isfinite(margin) or margin < 0:
            raise ValueError("Unit cost and profit margin must be finite, nonnegative numbers")
        cost = unit_cost * qty
        selling = cost * (1 + margin / 100)
        _set_value(row, "total_cost", cost)
        _set_value(row, "target_selling_price", selling)
        total_cost += cost
        total_selling += selling
        if group is not None:
            _set_value(group, "total_cost", group.get("total_cost") + cost)
            _set_value(group, "target_selling_price", group.get("target_selling_price") + selling)
    return total_cost, total_selling
