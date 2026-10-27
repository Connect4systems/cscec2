def get_data():
    return {"fieldname": "project", "internal_links": {"Project": "project", "Project Contract": "project_contract",
        "Sales Invoice": "invoice", "Journal Entry": "deduction_entry"},
        "transactions": [{"label": "Sources", "items": ["Project", "Project Contract"]},
            {"label": "Accounting", "items": ["Sales Invoice", "Journal Entry"]}]}
