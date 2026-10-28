"""Bundled master data. Existing records are preserved on repeated imports."""
import json
from pathlib import Path

DATA = Path(__file__).parent / 'data'
COST_TYPES = ('Equipments', 'Labour', 'Material', 'Subcontractor')


def load_records(filename):
    return json.loads((DATA / filename).read_text(encoding='utf-8'))


def ordered_cost_codes(rows):
    """Validate the entire hierarchy and return parents before children."""
    by_name = {r['cost_code']: r for r in rows}
    if len(by_name) != len(rows):
        raise ValueError('Duplicate cost codes in the import')
    ordered, visiting, done = [], set(), set()

    def visit(name):
        if name in done:
            return
        if name in visiting:
            raise ValueError('Circular cost code hierarchy')
        visiting.add(name)
        row = by_name[name]
        parent = row.get('parent_cost_code')
        if parent:
            if parent not in by_name or not by_name[parent].get('is_group'):
                raise ValueError(f'Invalid parent for cost code {name}: {parent}')
            visit(parent)
        ordered.append(row)
        visiting.remove(name)
        done.add(name)

    for name in by_name:
        visit(name)
    return ordered


def seed_divisions():
    import frappe
    for row in load_records('divisions.json'):
        if not frappe.db.exists('Division', row['title']):
            frappe.get_doc(dict(doctype='Division', **row)).insert(ignore_permissions=True)


def seed_cost_codes():
    import frappe
    rows = ordered_cost_codes(load_records('cost_codes.json'))
    company = frappe.db.get_value('Company', {'abbr': 'C'}, 'name')
    if not company:
        frappe.throw('Cost Code import requires the workbook company (Company abbreviation C). Create that Company before running the import.')
    parent = 'Project Cost - C'
    existing_parent = frappe.db.get_value('Cost Center', parent, ['company', 'is_group'], as_dict=True)
    if existing_parent and (existing_parent.company != company or not existing_parent.is_group):
        frappe.throw('Project Cost - C must be a group Cost Center in the company with abbreviation C')
    if not existing_parent:
        root = frappe.db.get_value('Cost Center', {'company': company, 'is_group': 1, 'parent_cost_center': ['is', 'not set']}, 'name')
        if not root:
            frappe.throw('Create the root Cost Center for the company with abbreviation C before importing cost codes')
        frappe.get_doc(dict(doctype='Cost Center', cost_center_name='Project Cost', company=company,
            parent_cost_center=root, is_group=1)).insert(ignore_permissions=True)
    for title in COST_TYPES:
        name = f'{title} - C'
        existing = frappe.db.get_value('Cost Center', name, ['company', 'parent_cost_center', 'is_group'], as_dict=True)
        if existing:
            if existing.company != company or existing.parent_cost_center != parent or existing.is_group:
                frappe.throw(f'{name} must be a leaf Cost Center under {parent}')
        else:
            frappe.get_doc(dict(doctype='Cost Center', cost_center_name=title, company=company,
                parent_cost_center=parent, is_group=0)).insert(ignore_permissions=True)
    for row in rows:
        if not frappe.db.exists('Cost Code', row['cost_code']):
            parent_code = row.get('parent_cost_code')
            if parent_code and not frappe.db.get_value('Cost Code', parent_code, 'is_group'):
                frappe.throw(f'Existing parent Cost Code {parent_code} must be a group')
            frappe.get_doc(dict(doctype='Cost Code', **row)).insert(ignore_permissions=True)
