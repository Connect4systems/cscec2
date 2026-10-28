from . import __version__ as app_version

app_name = 'contractor'
app_title = 'Contractor App'
app_publisher = 'Jenan Alfahham'
app_description = 'Contractor App'
app_email = 'jenan_fh95@hotmail.com'
app_license = 'MIT'

# Purchasing documents retain naming only; native trading forms have no app fields.
fixtures = [{'dt': 'Custom Field',
  'filters': [['name',
               'in',
               ['Project-total_expense_claim',
                'Project-custom_tab_4',
                'Project-custom_section_break_vvc4f',
                'Project-engineering_consulting_office',
                'Item-custom_type',
                'Project-custom_territory_',
                'Project-custom_warehouse',
                'Project-custom_column_break_gjdzd',
                'Project-project_classification',
                'Project-number',
                'Project-date',
                'Item-custom_column_break_d9gqr',
                'Project-custom_contract_type',
                'Project-custom_dashboard',
                'Project-custom_section_break_88zbr',
                'Project-custom_location',
                'Project-contracting',
                'Project-project_processing_status',
                'Project-base_project_amount',
                'Project-advance_payment_discount',
                'Project-business_guarantee_insurance_deduction_rate',
                'Project-project_amount',
                'Project-column_break_vxgcb',
                'Project-final_insurance_percentage',
                'Project-final_insurance_amount',
                'Item-custom_item_group_abbreviation_',
                'Project-custom_contract_items',
                'Project-group_items',
                'Project-custom_section_break_n9xrw',
                'Project-items',
                'Project-custom_teamwork',
                'Project-custom_project_manager',
                'Project-custom_pm_name',
                'Project-custom_email',
                'Item-custom_boq_id',
                'Project-custom_column_break_hlrtd',
                'Item-custom_parent_boq',
                'Project-custom_technical_office',
                'Project-custom_to_name',
                'Project-custom_toemail',
                'Item-custom_project',
                'Project-custom_section_break_hk0ef',
                'Item-is_group',
                'Item-group_item',
                'Item-custom_boq',
                'Project-project_clauses_tab',
                'Project-project_contract',
                'Project-tender_analysis',
                'Project-project_offer',
                'Project-project_contract_currency',
                'Project-project_clauses',
                'Project-project_clause_groups',
                'Project-custom_abbreviation']]]},
 {'dt': 'DocType Link',
  'filters': [['name', 'in', ['project-project-clearnce', 'project-subcontract-clearnce']]]}]

doctype_js = {'Project': 'public/js/doctype/project.js',
 'Item': 'public/js/doctype/item.js',
 'Material Request': 'public/js/doctype/material_request_comparison.js',
 'Comparison': 'public/js/doctype/comparison_table.js'}

override_doctype_class = {'Material Request': 'contractor.overrides.material_request.CustomMaterialRequest',
 'Stock Entry': 'contractor.overrides.stock_entry.CustomStockEntry',
 'Subcontractor Custody': 'contractor.overrides.subcontractor_custody.CustomSubcontractorCustody',
 'CR': 'contractor.overrides.cr.CustomCR',
 'Subcontractor Contract': 'contractor.overrides.subcontractor_contract.CustomSubcontractorContract',
 'CR Comparison': 'contractor.overrides.cr_comparison.CustomCRComparison',
 'Purchase Order': 'contractor.overrides.purchase_order.CustomPurchaseOrder',
 'Purchase Receipt': 'contractor.overrides.purchase_receipt.CustomPurchaseReceipt'}

doc_events = {'Project': {'validate': 'contractor.project_progress.validate_project',
             'after_insert': 'contractor.api.share_project_users',
             'on_update': 'contractor.api.share_project_users'}}

after_migrate = ['contractor.patches.project_abbreviation.execute']
