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
