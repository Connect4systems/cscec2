def get_data():
    return {
        'fieldname': 'project_budget',
        'internal_links': {'Project Contract': 'project_contract', 'Project': 'project',
            'Tender Analysis': 'tender_analysis', 'Costing Note': ['clauses', 'costing_note'],
            'BOQ': ['clauses', 'boq']},
        'transactions': [{'label': 'Sources', 'items': ['Project Contract', 'Project',
            'Tender Analysis', 'Costing Note', 'BOQ']}],
    }
