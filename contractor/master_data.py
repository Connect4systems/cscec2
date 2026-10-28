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


def resolve_company(company=None):
    import frappe
    company = company or frappe.db.get_single_value('Global Defaults', 'default_company')
    if not company:
        companies = frappe.get_all('Company', pluck='name', limit_page_length=2)
        if len(companies) == 1:
            company = companies[0]
    if not company:
        frappe.throw('Set Default Company in Global Defaults before importing Cost Codes (or pass company explicitly).')
    abbreviation = frappe.db.get_value('Company', company, 'abbr')
    if not abbreviation:
        frappe.throw(f'Company {company} has no abbreviation')
    return company, abbreviation


def remap_cost_type(row, abbreviation):
    result = dict(row)
    if result.get('cost_type'):
        title = result['cost_type'].removesuffix(' - C')
        if title not in COST_TYPES:
            raise ValueError(f'Unknown workbook Cost Type: {result["cost_type"]}')
        result['cost_type'] = f'{title} - {abbreviation}'
    return result


def seed_cost_codes(company=None):
    import frappe
    rows = ordered_cost_codes(load_records('cost_codes.json'))
    company, abbreviation = resolve_company(company)
    parent = f'Project Cost - {abbreviation}'
    existing_parent = frappe.db.get_value('Cost Center', parent, ['company', 'is_group'], as_dict=True)
    if existing_parent and (existing_parent.company != company or not existing_parent.is_group):
        frappe.throw(f'{parent} must be a group Cost Center in {company}')
    if not existing_parent:
        root = frappe.db.get_value('Cost Center', {'company': company, 'is_group': 1, 'parent_cost_center': ['is', 'not set']}, 'name')
        if not root:
            frappe.throw(f'Create the root Cost Center for {company} before importing cost codes')
        frappe.get_doc(dict(doctype='Cost Center', cost_center_name='Project Cost', company=company,
            parent_cost_center=root, is_group=1)).insert(ignore_permissions=True)
    for title in COST_TYPES:
        name = f'{title} - {abbreviation}'
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
            frappe.get_doc(dict(doctype='Cost Code', **remap_cost_type(row, abbreviation))).insert(ignore_permissions=True)
