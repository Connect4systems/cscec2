"""Project Budget arithmetic, independent of Frappe and selling prices."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import math

from contractor.tender_logic import number_rows

CATEGORIES = {
    'material': 'total_material_costs',
    'labour': 'total_labor_costs',
    'subcontractor': 'total_contractors',
    'other_expenses': 'total_expenses',
    'equipment': 'custom_total_equipment_costs',
}
BUDGET_FIELDS = tuple(name + '_budget' for name in CATEGORIES) + ('total_cost',)
UNIT_FIELDS = tuple('unit_' + name + '_cost' for name in CATEGORIES) + ('unit_cost',)


def number(value, label, positive=False):
    try:
        result = Decimal(str(value if value is not None else 0))
    except (InvalidOperation, ValueError):
        raise ValueError(f'{label} must be a finite nonnegative number')
    if not result.is_finite() or not math.isfinite(float(result)) or result < 0 or (positive and result == 0):
        raise ValueError(f'{label} must be finite and {"positive" if positive else "nonnegative"}')
    return result


def amounts_match(left, right, precision=2):
    return abs(number(left, 'Cost') - number(right, 'Cost')) <= Decimal(1).scaleb(-precision)


def build_budget(clauses, boqs, precision=2):
    """Multiply BOQ unit category costs by final contract quantities, once."""
    quantum = Decimal(1).scaleb(-precision)
    result = []
    totals = {field: Decimal(0) for field in BUDGET_FIELDS}
    group = None
    for source in clauses:
        row = {key: source.get(key) for key in ('is_group', 'series_number', 'parent_series',
            'clause_title', 'contractual_clause', 'qty', 'uom', 'source_row')}
        row['contract_clause_row'] = source.get('name')
        for field in BUDGET_FIELDS + UNIT_FIELDS:
            row[field] = 0
        if source.get('is_group'):
            row['qty'] = 0
            group = row
        else:
            qty = number(source.get('qty'), 'Contract quantity', positive=True)
            boq = boqs.get(source.get('name'))
            if not boq:
                raise ValueError('Every detail clause requires its submitted BOQ')
            components = {name: number(boq.get(field), f'BOQ {name} cost') for name, field in CATEGORIES.items()}
            unit_cost = number(boq.get('total_cost'), 'BOQ total unit cost')
            if not amounts_match(sum(components.values(), Decimal(0)), unit_cost, max(precision, 6)):
                raise ValueError('BOQ category costs do not reconcile with its total unit cost')
            row['qty'] = float(qty)
            row['unit_cost'] = float(unit_cost)
            row['boq'] = boq.get('name')
            try:
                amounts = {name: (qty * cost).quantize(quantum, rounding=ROUND_HALF_UP)
                    for name, cost in components.items()}
                total = (qty * unit_cost).quantize(quantum, rounding=ROUND_HALF_UP)
            except InvalidOperation:
                raise ValueError('Budget amount exceeds supported precision')
            # Allocate category rounding so the split equals quantity x BOQ unit cost.
            difference = total - sum(amounts.values(), Decimal(0))
            for name in sorted(components, key=lambda name: components[name], reverse=True):
                adjustment = difference if difference >= 0 else max(difference, -amounts[name])
                amounts[name] += adjustment
                difference -= adjustment
                if not difference:
                    break
            for name, cost in components.items():
                row['unit_' + name + '_cost'] = float(cost)
                row[name + '_budget'] = float(amounts[name])
            row['total_cost'] = float(total)
            for field in BUDGET_FIELDS:
                amount = Decimal(str(row[field]))
                totals[field] += amount
                if group is not None:
                    group[field] = float(Decimal(str(group[field])) + amount)
        result.append(row)
    if not any(not row.get('is_group') for row in result):
        raise ValueError('The contract must contain at least one detail clause')
    number_rows(result, 'From Excel')
    summary = {'total_project_budget': float(totals['total_cost'])}
    for name in CATEGORIES:
        summary['total_' + name] = float(totals[name + '_budget'])
    return result, summary
