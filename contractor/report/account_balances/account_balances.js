// contractor/report/account_balances/account_balances.js

frappe.query_reports["Account Balances"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": "Company",
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1
        }
    ]
}
