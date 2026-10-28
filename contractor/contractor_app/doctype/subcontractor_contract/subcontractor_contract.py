from contractor.contractor_app.doctype.cr.cr import CR


class SubcontractorContract(CR):
    def validate(self):
        super().validate()
        from contractor.subcontracting import validate_contract
        validate_contract(self)

    def before_cancel(self):
        import frappe
        from contractor.project_clearances import lock_project
        lock_project(self.project)
        if frappe.db.exists('Subcontract Clearnce', {'subcontractor_contract': self.name, 'docstatus': ['!=', 2]}):
            frappe.throw('Cancel or delete linked Subcontract Clearnces before cancelling the contract')
