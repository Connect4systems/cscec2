from frappe.model.document import Document


class ProjectBudget(Document):
    def validate(self):
        from contractor.project_budget import validate_budget
        validate_budget(self)

    def on_cancel(self):
        self.db_set('status', 'Cancelled', update_modified=False)
