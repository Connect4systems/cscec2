"""Resource quantities and cost bases shared by BOQ pricing and Project Budget."""
import math

TABLE_TOTALS = {
    'material_costs': 'total_material_costs', 'labor_costs': 'total_labor_costs',
    'contractors_table': 'total_contractors', 'expenses_table': 'total_expenses',
    'custom_equipment': 'custom_total_equipment_costs',
}


def _set(row, field, value):
    if isinstance(row, dict):
        row[field] = value
    else:
        row.set(field, value)


def _number(value, label, positive=False):
    try:
        result = float(value or 0)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f'{label} must be a finite nonnegative number')
    if not math.isfinite(result) or result < 0 or (positive and result <= 0):
        raise ValueError(f'{label} must be finite and {"positive" if positive else "nonnegative"}')
    return result


def calculate_resources(boq, convert_legacy=False):
    basis = boq.get('quantity_basis') or 'Per Unit'
    if basis not in ('Per Unit', 'Project Quantity'):
        raise ValueError('Invalid BOQ quantity basis')
    project_mode = basis == 'Project Quantity' or convert_legacy
    project_qty = _number(boq.get('project_qty'), 'Project Quantity', positive=project_mode)
    total = 0
    for table, total_field in TABLE_TOTALS.items():
        subtotal = 0
        for row in boq.get(table) or []:
            if project_mode:
                # Old draft rows stored a coefficient in qty; preserve it on conversion.
                coefficient = row.get('qty') if basis != 'Project Quantity' else row.get('per_unit_qty')
                coefficient = _number(coefficient, 'Resource quantity per unit')
                _set(row, 'per_unit_qty', coefficient)
                qty = coefficient * project_qty
                _set(row, 'qty', qty)
            else:
                qty = _number(row.get('qty'), 'Resource quantity')
            rate = _number(row.get('cost'), 'Resource rate')
            amount = qty * rate
            if not math.isfinite(amount):
                raise ValueError('Resource total exceeds supported precision')
            _set(row, 'total_cost', amount)
            subtotal += amount
        _set(boq, total_field, subtotal)
        total += subtotal
    if not math.isfinite(total):
        raise ValueError('BOQ total exceeds supported precision')
    _set(boq, 'total_cost', total)
    _set(boq, 'quantity_basis', 'Project Quantity' if project_mode else 'Per Unit')
    _set(boq, 'unit_cost', total / project_qty if project_mode else total)
    _set(boq, 'project_total_cost', total if project_mode else total * project_qty)
    return boq


def unit_costs(boq):
    basis = boq.get('quantity_basis') or 'Per Unit'
    if basis not in ('Per Unit', 'Project Quantity'):
        raise ValueError('Invalid BOQ quantity basis')
    project_mode = basis == 'Project Quantity'
    divisor = _number(boq.get('project_qty'), 'Project Quantity', positive=True) if project_mode else 1
    values = {field: _number(boq.get(field), 'BOQ category cost') / divisor for field in TABLE_TOTALS.values()}
    values['total_cost'] = _number(boq.get('total_cost'), 'BOQ total cost') / divisor
    values['name'] = boq.get('name')
    return values
