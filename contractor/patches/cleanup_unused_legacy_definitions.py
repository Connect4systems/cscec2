"""Remove retired definitions only after checking usage on the actual site."""
import frappe


def execute():
    from contractor.app_cleanup import retire_unused_doctypes
    for result in retire_unused_doctypes():
        if result.get("removed"):
            print(f"Removed unused DocType: {result['doctype']}")
        elif result["exists"]:
            print(f"Retained {result['doctype']}: {'; '.join(result['reasons'])}")
    frappe.clear_cache()
