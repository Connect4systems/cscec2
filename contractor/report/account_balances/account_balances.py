# contractor/report/account_balances/account_balances.py

import frappe

def execute(filters=None):
    if not filters or not filters.get("company"):
        frappe.throw("Please select a Company to view the report.")

    columns = [
        {"label": "Account", "fieldname": "account", "fieldtype": "Link", "options": "Account"},
        {"label": "Account Name", "fieldname": "account_name", "fieldtype": "Data"},
        {"label": "Balance", "fieldname": "balance", "fieldtype": "Currency"}
    ]

    data = frappe.db.sql("""
        SELECT
            name AS account,
            account_name,
            (total_debit - total_credit) AS balance
        FROM
            `tabAccount`
        WHERE
            is_group = 0
            AND company = %s
        ORDER BY account_name
    """, (filters.get("company"),), as_dict=True)

    return columns, data
