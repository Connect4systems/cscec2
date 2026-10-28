from contractor.legacy.customer_clearance import Clearence
from contractor.project_clearances import validate_clearance, submit_clearance, cancel_clearance, lock_project


class ProjectClearnce(Clearence):
    def validate(self):
        if self.get("legacy_record"):
            return super().validate()
        validate_clearance(self)

    def on_submit(self):
        if self.get("legacy_record"):
            return super().on_submit()
        submit_clearance(self)

    def before_cancel(self):
        if not self.get("legacy_record"):
            lock_project(self.project)

    def on_cancel(self):
        if self.get("legacy_record"):
            return super().on_cancel()
        cancel_clearance(self)
