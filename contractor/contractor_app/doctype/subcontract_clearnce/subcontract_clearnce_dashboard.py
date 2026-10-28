def get_data():
    return {"fieldname": "project", "internal_links": {"Project": "project", "Project Contract": "project_contract", "Subcontractor Contract": "subcontractor_contract",
        "Purchase Invoice": "invoice", "Journal Entry": "deduction_entry"},
        "transactions": [{"label": "Sources", "items": ["Project", "Project Contract", "Subcontractor Contract"]},
            {"label": "Accounting", "items": ["Purchase Invoice", "Journal Entry"]}]}
