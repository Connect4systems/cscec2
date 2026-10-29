"""Legacy mappings must bind document names as SQL values."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class LegacyClearanceQueriesTest(unittest.TestCase):
    def setUp(self):
        self.frappe = types.ModuleType("frappe")
        self.frappe.whitelist = lambda: lambda fn: fn
        self.frappe.flags = types.SimpleNamespace(args=types.SimpleNamespace())
        self.frappe.db = MagicMock()
        self.frappe.db.sql.return_value = []
        utils = types.ModuleType("frappe.utils")
        utils.today = MagicMock()
        utils.flt = float
        mapper = types.ModuleType("frappe.model.mapper")
        mapper.get_mapped_doc = MagicMock()
        mapper.get_mapped_doc.return_value.items = [
            types.SimpleNamespace(is_group=0, item_code="ITEM-1", qty=10)
        ]
        boq = types.ModuleType("contractor.contractor_app.doctype.boq.boq")
        boq.set_boq_template = MagicMock()
        spec = importlib.util.spec_from_file_location(
            "legacy_clearance_api_test",
            Path(__file__).parents[1] / "contractor/www/api.py",
        )
        self.api = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {
            "frappe": self.frappe, "frappe.utils": utils,
            "frappe.model.mapper": mapper,
            "contractor.contractor_app.doctype.boq.boq": boq,
        }):
            spec.loader.exec_module(self.api)

    def test_document_names_are_bound_for_all_clearance_sources(self):
        source_name = "Client's order' OR 1=1 --"
        for doctype, column in (
            ("Sales Order", "sales_order"),
            ("Project", "project"),
            ("Purchase Order", "purchase_order"),
        ):
            with self.subTest(doctype=doctype):
                self.frappe.flags.args.doctype = doctype
                if doctype == "Purchase Order":
                    self.api.create_purchase_clearence(source_name)
                else:
                    self.api.create_clearence(source_name)
                args, kwargs = self.frappe.db.sql.call_args
                self.assertIn(f"c.{column} = %s", args[0])
                self.assertNotIn(source_name, args[0])
                self.assertEqual(args[1], (source_name,))
                self.assertEqual(kwargs, {"as_dict": 1})
