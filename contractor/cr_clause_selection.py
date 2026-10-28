"""Choose Project clause rows while retaining their heading and original order."""


def select_project_rows(rows, fetch_all=True, selected_rows=None):
    if fetch_all:
        return rows
    if not isinstance(selected_rows, list) or not selected_rows or any(not isinstance(name, str) for name in selected_rows):
        raise ValueError('Select at least one detail clause')
    selected = set(selected_rows)
    details = {row.get('name'): row for row in rows if not row.get('is_group')}
    if not selected.issubset(details):
        raise ValueError('Selected clauses must be detail clauses from the current Project')
    groups = {details[name].get('parent_series') for name in selected}
    return [row for row in rows if (row.get('is_group') and row.get('series_number') in groups)
            or (not row.get('is_group') and row.get('name') in selected)]



def selected_quantities(rows, quantities=None):
    import math
    if quantities is None:
        return {}
    if not isinstance(quantities, dict):
        raise ValueError('Clause quantities must be an object keyed by selected clause row')
    details = {row.get('name') for row in rows if not row.get('is_group')}
    if not set(quantities).issubset(details):
        raise ValueError('Quantities can only be changed for selected detail clauses')
    result = {}
    for name, value in quantities.items():
        try:
            qty = float(value)
        except (TypeError, ValueError, OverflowError):
            raise ValueError('Selected clause quantities must be greater than zero')
        if isinstance(value, bool) or not math.isfinite(qty) or qty <= 0:
            raise ValueError('Selected clause quantities must be greater than zero')
        result[name] = qty
    return result


def merge_project_clauses(existing, incoming):
    """Keep existing row objects and insert new details under their source heading."""
    merged = list(existing)
    seen = {row.get('project_clause') for row in merged if row.get('project_clause')}
    used = {str(row.get('series_number')) for row in merged}
    source_group = None
    target_group = None
    for row in incoming:
        source = row.get('project_clause')
        if row.get('is_group'):
            source_group = row.get('series_number')
            target_group = next((item for item in merged if item.get('is_group')
                and item.get('project_clause') == source), None)
            if target_group is None:
                row = dict(row)
                series = str(source_group)
                if series in used:
                    series = str(max([int(item.get('series_number')) for item in merged
                        if item.get('is_group')] or [0]) + 1)
                row['series_number'] = series
                row['parent_series'] = ''
                merged.append(row)
                used.add(series)
                seen.add(source)
                target_group = row
            continue
        if source in seen:
            continue
        if target_group is None or row.get('parent_series') != source_group:
            raise ValueError('A selected clause is missing its source group')
        row = dict(row)
        parent = str(target_group.get('series_number'))
        suffix = str(row.get('series_number')).split('_')[-1]
        series = f'{parent}_{suffix}'
        if series in used:
            suffix = 1
            while f'{parent}_{suffix}' in used:
                suffix += 1
            series = f'{parent}_{suffix}'
        row['series_number'] = series
        row['parent_series'] = parent
        # Insert after the last existing detail of this heading, before the next heading.
        position = next(i for i, item in enumerate(merged) if item is target_group) + 1
        while position < len(merged) and not merged[position].get('is_group'):
            position += 1
        merged.insert(position, row)
        used.add(series)
        seen.add(source)
    return merged
