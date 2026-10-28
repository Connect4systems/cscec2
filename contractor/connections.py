"""Native Frappe dashboard routes for the tender commercial workflow."""


def dashboard_data(doctype):
    if doctype == "Costing Note":
        return {
            "fieldname": "costing_note",
            "internal_links": {"Tender Analysis": "tender_analysis"},
            "transactions": [
                {"label": "Sources", "items": ["Tender Analysis"]},
                {"label": "Pricing", "items": ["BOQ"]},
            ],
        }
    if doctype == "Project Offer":
        return {
            "fieldname": "project_offer",
            "internal_links": {"Tender Analysis": "tender_analysis", "Costing Note": ["clauses", "costing_note"]},
            "transactions": [
                {"label": "Sources", "items": ["Tender Analysis", "Costing Note"]},
                {"label": "Contracts", "items": ["Project Contract"]},
            ],
        }
    if doctype == "Project Contract":
        return {
            "fieldname": "project_contract",
            "internal_links": {"Tender Analysis": "tender_analysis", "Project Offer": "project_offer",
                "Costing Note": ["clauses", "costing_note"]},
            "transactions": [
                {"label": "Sources", "items": ["Tender Analysis", "Project Offer", "Costing Note"]},
                {"label": "Execution", "items": ["Project"]},
                {"label": "Budgets", "items": ["Project Budget"]},
                {"label": "Certificates", "items": ["Project Clearnce", "Subcontract Clearnce"]},
            ],
        }
    raise ValueError(f"Unsupported connection dashboard: {doctype}")
