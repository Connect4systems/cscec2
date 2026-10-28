# Project-cycle usage review

This is the pre-cleanup review snapshot. The subsequent authorized cleanup and
retained feature decisions are documented in [app-cleanup.md](app-cleanup.md).
Purchase Comparison, Item Coding Request, Subcontractor Custody, and Account
Balances source are retained.

Reviewed: 28 October 2026. Scope: this repository, not a live Frappe database.
No application definitions, records, hooks, or scripts were deleted or changed by
this review. The evidence is shipped schemas, Link/Table options, hooks, Jinja
includes, Python imports/API calls, workspaces, fixture exports, and migrations.
Dynamic/site-owned Client Scripts, Server Scripts, Print Formats, Workflows,
custom reports, external API callers, saved preferences, and existing business
records were not available for inspection.

The current cycle is:

`Tender Analysis -> Costing Note / BOQ -> Project Offer -> Project Contract -> Project`

`Project -> CR -> Subcontractor Contract -> Subcontract Clearnce`

`Project -> Project Clearnce -> Sales Invoice / deduction journal`

`Subcontract Clearnce -> Purchase Invoice / deduction journal`

Direct subcontract contracts, Project procurement, stock/custody operations, and
supporting masters are also considered. Project Offer is optional where the direct
Project Contract action is used.

## Inventory

The [complete inventory](project-cycle-inventory.csv) has 198 entries, including
all 56 DocTypes, all 95 custom-field fixture records, the 3 connection fixtures,
11 public client scripts, 8 controller overrides, 18 empty DocType client scripts,
5 customization exports, the empty property-setter fixture, and the report folder.

| DocType classification | Count |
| --- | ---: |
| Current core cycle | 28 |
| Optional procurement, inventory, or Project master/support | 13 |
| Retained item-based legacy dependencies | 7 |
| No incoming repository consumers found | 5 |
| Seeded master without form integration | 1 |
| Old tax child table used by migration | 1 |
| HR/vehicle feature outside the Project cycle | 1 |
| Total | 56 |

## 1. DocTypes not used by the current Project cycle

### Strongest unused-code candidates

These five have schemas but no external shipped Link/Table consumer, workspace
entry, or business-code caller was found. Their own controllers and self-links do
not establish a Project-cycle use. This does not prove the live site has no data or
custom consumers.

| DocType | Evidence | Recommendation |
| --- | --- | --- |
| Deduction Table | No parent Table field references it; current contracts/certificates use **Deduction** | Candidate for retirement after site checks |
| Project Engineer | No incoming reference; Project manager/technical-office fields link **Employee** | Candidate for retirement after site checks |
| Purchase Category | No incoming reference | Candidate for retirement after site checks |
| Type | Only its own definition/controller and self-amendment link; current contract classification uses **Contract Type** | Candidate for retirement after site checks |
| Workflow img | Standalone Single containing purchase_request and image; no app consumer | Check saved Single values and custom consumers before retirement |

Definitions are under `contractor/contractor_app/doctype/` with the corresponding
`deduction_table`, `project_engineer`, `purchase_category`, `type`, and `workflow_img`
folders.

### Not integrated, superseded, or outside this cycle

| DocType | Current status | Recommendation |
| --- | --- | --- |
| Division | Created and seeded by master_data.py, but no shipped Link/Table field targets **Division**. Fields labelled Division still target Item | Integrate it if needed; do not treat recently seeded master data as disposable |
| Project Contract Tax | No current tax table uses it; standard_project_contract_taxes.py reads it to migrate historical rows to Sales Taxes and Charges | Keep through migration/history verification; not a current operational tax table |
| Car Use Request | Employee/vehicle request exposed by Operation Director workspace | Outside the contracting cycle, but still a separate available feature |
| E-Language, Edu | No JSON schemas shipped; small compatibility controllers remain; app_cleanup.py checks these two against live-site usage | Already retired from installation definitions; preserve site data and compatibility until verified |

### Legacy dependencies that are not used for new clause rows

| Definition | Why it remains |
| --- | --- |
| BOQ ID | Item and Material Request Item custom fields still reference it; Sales Order references are hidden |
| Project Item | Historical Project.items table and legacy Project/Costing Note mappings |
| Group Item | Historical Project, Costing Note, certificate, and hidden Sales Order grouping |
| Clearence Item | Historical customer certificate items |
| Purchase Clearence Item | Historical supplier certificate items |
| Clearence Items Summary | Historical certificate summaries |
| Clearence Type | Link from the two historical certificate-item tables |

The current certificate controllers explicitly import the legacy clearance
controllers and branch on `legacy_record`. Removing these definitions or their
supporting code would therefore be different from removing unused files.

## 2. Fixtures not used in the new contracting cycle

### Hidden retired contracting fields

`contractor/fixtures/custom_field.json` contains 35 hidden retired contracting or
grouping fields across the following targets. They preserve old stored values and
are intentionally no longer the new tender/contracting interface.

| Target | Fields |
| --- | --- |
| Opportunity Item (5) | is_group, series_number, parent_group, group_item, item_description |
| Opportunity (2) | group_items, section_break_7gqac |
| Quotation Item (4) | is_group, series_number, parent_group, group_item |
| Sales Order Item (9) | boq_id, is_group, cost_code, series_number, parent_group, group_item, custom_boq_description, custom_cost_code, custom_boq_no |
| Sales Order (15) | boq_id, cost_code, contractor_order, contracting_section, advance_payment_discount, column_break_vxgcb, business_guarantee_insurance_deduction_rate, section_break_7gqac, group_items, contracting_settings, selling_deductions_template, deductions, sect_totals, base_total_deductions, total_deductions |

Source evidence: `retire_opportunity_pricing.py`, `retire_quotation_contracting.py`,
`retire_sales_order_contracting.py`, and `retired_sales_order_fields.json`.
Hidden workflow_state fields are **not** included in this unused grouping list;
workflow metadata can still be required by the site's approval workflow.

### Other fixture/export findings

| File or group | Finding |
| --- | --- |
| fixtures/property_setter.json | Empty array: zero exported records. Its hook entry currently exports only Opportunity Item/Sales Order Item setters |
| fixtures/doctype_link.json | The Opportunity -> Project Clearnce relationship belongs to the older path; Project -> Project Clearnce and Project -> Subcontract Clearnce are active |
| contractor_app/custom/boq_id.json | Two stale property setters target item and naming_series, neither of which exists in the shipped BOQ ID schema |
| contractor_app/custom/material_request_item.json | Hidden legacy boq/work_pakage settings and a boq_id fetch from boq.custom_boq_id; current Cost Code/cost-center settings are mixed into the same export |
| contractor_app/custom/material_request.json | Hidden old custom_boq/custom_work_package/custom_get_items fields coexist with active Project/Comparison settings; company default is site-specific CSCEC |
| Project legacy items/group_items/contracting amount fields | Older item-based Project behavior, not the current clause/progress tables; some money fields are hidden by the Project client script for clause Projects |
| Item custom_type/custom_boq_id/custom_parent_boq/is_group/group_item | Older Item-based BOQ/grouping support; not the current clause identity, but still connected to retained Item/BOQ and procurement customizations |
| fixtures/custom_field.json and contractor_app/custom/project.json | Overlapping Project-field exports. Duplication is a maintenance issue, not proof that either entire export is unused |

Do not remove `custom/deduction.json`: it sets active Deduction.percent precision.
Do not remove the entire Project customization export: it supplies the current
Project clause snapshots, source links, summary table, and abbreviation.
An empty `fixtures/property_setter.json` does not mean there are no property
setters: the five customization exports also contain property setters and sync
on migration.

## 3. Scripts outside the current cycle or with no current loader

| Script | Finding | Treatment |
| --- | --- | --- |
| public/js/doctype/material_request.js | No hook/include points to it. hooks.py loads material_request_comparison.js instead; the older script contains a different comparison/BOQ flow | Strong cleanup candidate, subject to site Client Script references |
| overrides/purchase_order.py | CustomPurchaseOrder is not registered in override_doctype_class and has no repository import | Strong cleanup candidate, subject to site references |
| public/js/doctype/sales_invoice.js | Still hooked, but its contractor_order/clearence deduction action is the old invoice flow. New clearance accounting creates native invoices with contractor_order=0 | Legacy behavior, not dead registration; retain until history/site actions are reviewed |
| public/js/doctype/item.js | Still hooked; filters the legacy group_item field | Outside clause header logic, but loaded and linked to retained grouping |
| www/api.py: make_project | Old mapped Project creation; no current shipped caller found. New Project creation uses contract_projects.py | Legacy public API candidate; check external/site callers |
| www/api.py: create_purchase_clearence | Old purchasing mapping; no current shipped caller found. Current actions use subcontracting.create_clearance or project_clearances | Legacy public API candidate; check external/site callers |
| www/api.py: validate / on_update_after_submit | Not connected through the current doc_events hook | Unregistered legacy event entrypoints; do not delete their shared helper functions blindly |
| doctype/e_language/e_language.py, doctype/edu/edu.py | Controllers left after retirement of installation schemas | Compatibility remnants |

`www/api.py` is a mixed module, not an unused file: Project's legacy actions,
Costing Note's legacy BOQ action, Sales Invoice deductions, and the legacy customer
clearance import still consume parts of it.

`legacy/customer_clearance.py`, `legacy/supplier_clearance.py`, and the old
`doctype/clearence/clearence.py` / `doctype/purchase_clearence/purchase_clearence.py`
API shims remain reachable. They are outside new certificate calculations but
must not be described as unreferenced.

The following DocType JavaScript files contain only comments or an empty event
map, with no business behavior:

- boq_id/boq_id.js
- car_use_request/car_use_request.js
- clearence_type/clearence_type.js
- comparison/comparison.js
- cost_code/cost_code.js
- cr_comparison/cr_comparison.js
- engineering_consulting_office/engineering_consulting_office.js
- item_coding_request/item_coding_request.js
- project_classification/project_classification.js
- project_engineer/project_engineer.js
- project_processing_status/project_processing_status.js
- purchase_category/purchase_category.js
- purchasing_deductions_template/purchasing_deductions_template.js
- selling_deductions_template/selling_deductions_template.js
- site_material_request/site_material_request.js
- subcontractor_custody/subcontractor_custody.js
- type/type.js
- workflow_img/workflow_img.js

These paths are relative to `contractor/contractor_app/doctype/`. An empty client
script does not mean its DocType is unused. In particular, Comparison's behavior
is in the hooked comparison_table.js. Pass-only Python Document classes are
normal Frappe controllers and are not classified as unused merely for being small.

## 4. Reports

Only one custom report implementation folder was found:

| Report | Evidence | Current-cycle status |
| --- | --- | --- |
| Account Balances | contractor/report/account_balances/account_balances.py and .js | No Project filter, no workspace reference, and no packaged Report JSON. Its registration/use on the live site is unverified |

No standard `Report` JSON definition is shipped anywhere in this repository.
The Account Balances folder is also outside the module's usual
`contractor/contractor_app/report/` tree. Treat it as an unregistered/incomplete
repository report candidate rather than claiming no user has ever used it.

Constructions workspace links **Budget Variance Report** and **Project wise Stock
Tracking**. They are external/ERPNext report links, not unused custom report
implementations shipped by this app. Site-defined custom reports cannot be
inventoried from this checkout.

## 5. Current dependencies to keep

The 28 current-cycle DocTypes are listed individually in the CSV. In particular,
keep **Contract Type**, **Deduction**, **Contractors table**, the BOQ resource
children, both tax/deduction templates, and the new clause children. They are
actively used, even though some similarly named older definitions are candidates.

Optional Project-support features also have real consumers: Comparison/Supplier
Comparison/CR Comparison; Site Material Request and Cost Code; Subcontractor
Custody; Item Coding Request; Engineering consulting office; Project
Classification; and Project Processing Status.

Keep `contracting_audit.py`: it is a documented manual integrity check for current
Project certificates, invoices, and deduction journals. A utility does not become
unused merely because it is run manually rather than by a form button.
Keep registered patches and their data files: they are migration history, not
normal runtime actions. Keep the Project Abbreviation after_migrate repair.

## 6. Related review findings

- CR Comparison still links Contract Type to **Item Group**, whereas CR and
  Subcontractor Contract now link to **Contract Type**. This is a consistency
  gap in an optional retained flow, not evidence CR Comparison is unused.
- No form selects the **Division** master. CR Comparison's Division targets Item,
  and Subcontractor Contract's old Item-backed Division is hidden.
- docs/app-cleanup.md still says Contract Type is retired. This is outdated:
  the schema is restored, the new forms use it, and app_cleanup.py now retires only
  E-Language and Edu.
- project_contract_total was deliberately removed by the clause-progress
  migration. A live list-view query that still requests it would require inspecting
  saved site metadata/preferences; it is not a reason to restore it as an active
  Project commercial field.

## 7. Suggested cleanup order

1. Review the five unreferenced DocTypes, old unhooked Material Request client
   script, unregistered Purchase Order override, empty client scripts, and stale
   BOQ ID property setters first.
2. Decide whether Division should be integrated into a form. Preserve its seeded
   records until that decision is made.
3. Review hidden legacy fixture groups and historical tables against actual site
   records before retiring further exports or metadata.
4. Check live Custom Field/DocField links, Workflows, Client Scripts, Server Scripts,
   Print Formats, Reports, workspaces, API integrations, and saved preferences.
   For Workflow img, inspect Single values as well as links.
5. Keep legacy clearance dependencies, compatibility APIs, and migration files
   until their history and external consumers have been verified.

The existing `bench --site SITE execute contractor.app_cleanup.audit` is read-only
but covers only its existing retired definitions (E-Language/Edu) and Texture name
matches. It is not a live usage audit of all candidates in this report.

This review did not run migration or deletion commands and did not modify
application behavior. No new functional tests were needed for the report files.
