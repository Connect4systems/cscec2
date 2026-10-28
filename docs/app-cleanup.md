# App cleanup and retained dependencies

The current cycle covers Tender Analysis, Costing Note/BOQ, Project Offer,
Project Contract, Project, CR, Subcontractor Contract, Project Clearnce and
Subcontract Clearnce, native invoices, and deduction journals.

The authorized cleanup removes unused package definitions and code. It does not
remove stored business records or drop SQL business tables.

## Retained by request

- Purchase Comparison: Comparison, Supplier Comparison, hooked comparison_table.js,
  and the approved Material Request comparison action.
- Item Coding Request and its Item Code child table.
- Subcontractor Custody, its child table, and its stock-transfer override.
- Account Balances report source, pending a separate repair/registration decision.

The three requested features retain their empty client-script skeletons as well
as their working code. Contract Type and Deduction remain active masters. Division
remains as the seeded master requested earlier, even though no form currently
selects it.

## Removed from the package

- Installation JSON schemas for Deduction Table, Project Engineer, Purchase
  Category, Type, and Workflow img. Their small Python controllers remain so a
  site's retained metadata and records can still be opened.
- Fifteen comment-only or empty DocType JavaScript files. Active controllers and
  shared/hooked scripts are retained.
- Unhooked public/js/doctype/material_request.js. The active
  material_request_comparison.js remains hooked.
- Purchase Order and Purchase Receipt now retain only their requested Project-based
  autoname methods. Other purchase controller behavior remains native.
- Stale custom/boq_id.json export, whose item/naming_series targets are absent
  from the shipped BOQ ID schema.
- Empty fixtures/property_setter.json and its empty export hook.
- Thirty-five retired Opportunity/Quotation/Sales Order grouping and contracting
  custom-field fixture entries. Existing fields are hidden, not deleted, on a
  deployed site. Hooks now export only the 53 remaining named Custom Field
  records, preventing re-export of the retired definitions or unrelated site fields.
- Inactive commented hook scaffolding; active hooks are retained.

## Migration behavior

cleanup_project_cycle.py checks seven retirement candidates: E-Language, Edu,
Deduction Table, Project Engineer, Purchase Category, Type, and Workflow img.
It removes only app-owned standard metadata with no saved records/Single values,
external Link/Table references, connection references, native direct/dynamic links,
or detected literal references in site scripts/text configuration. Used definitions
are retained and their reasons are printed.

Single DocTypes are checked through saved tabSingles values, without querying a
nonexistent business table. Literal scans cover available Client Scripts, Server
Scripts, Print Formats, Reports, Workspaces, and Custom HTML Blocks. Computed
external/API references cannot be proven absent by a source or text scan.

The migration also hides existing retired fixture fields without deleting their
columns or values. It removes only the two former BOQ ID property setters when
their exact target fields still do not exist; site-defined target fields preserve
their setters. No accounting transactions are recalculated.

## Dependencies kept for history and current operations

Contractors table remains required for BOQ and Template BOQ subcontract costing.
Group Item, Project Item, Clearence Item, Purchase Clearence Item, Clearence Items
Summary, Clearence Type, BOQ ID, and Project Contract Tax remain for historical
schema references and migrations. Legacy certificate controllers and compatibility
API paths remain for historical compatibility. Sales Invoice's old deduction action
is no longer hooked. Purchase Receipt retains naming only; its former warehouse
override is removed.

All registered historical migration patches and their data files remain shipped.
Purchase comparison, item coding, custody, current clause flows, taxes, deductions,
and invoice posting are outside the removed-code set.

## Account Balances

The retained report code is intended to list company leaf accounts with Account,
Account Name, and Balance columns, calculating total_debit minus total_credit.
It has no Project/date filters and no packaged Report registration. Standard ERPNext
v15's Account schema does not provide those two totals, so the query needs repair
against ledger data or an accounting API before use. No report registration or
financial calculation changes are included in this cleanup.

## Deployment and verification

```bash
bench --site TEST_SITE execute contractor.app_cleanup.audit
bench --site TEST_SITE migrate
bench build --app contractor
bench --site TEST_SITE clear-cache
bench restart
```

The audit command is read-only. Review retention/removal results on a test copy of
the site before production migration. Refresh the browser after deployment.
Local checks cover cleanup guards, fixture scoping, preserved features, and the
existing project-cycle tests. Live migration and workflow checks still require a
configured Frappe site.


## Standard ERPNext documents

Opportunity, Quotation, Sales Order, Sales Invoice, Purchase Order, Purchase Invoice,
and Purchase Receipt now have no contractor fixture exports, form-script hooks,
or document-event hooks. Purchase Order and Purchase Receipt retain naming-only
controller overrides; the other five use native controllers without overrides. Their native item/tax tables are
included in restoration. Purchase Comparison, Item Coding Request, Subcontractor
Custody, and the custom Project/CR/contract/certificate flows remain available.

The standard_erpnext_documents patch removes known app-owned Custom Field metadata,
Property Setters, and connection overrides using a manifest traced from the app's
fixture history and retirement manifests. It force-reloads native ERPNext metadata.
Custom Field metadata removal does not drop its SQL column or historical values;
the fields stop appearing in native forms. No business documents are resaved.

Fields owned by another module and fields required by an active site Workflow are
retained and printed for administrator review. The app does not disable unrelated
workflows or delete other apps' fields. The seven documents use native controllers,
tax calculations and item tables. Purchase Order uses PO-<Project Abbreviation>-0001
and Purchase Receipt uses PRE-<Project Abbreviation>-0001. No Order Type field or
CO prefix is used, and the abbreviation comes from the native Project link. The Material Request Purchase Order helper
also delegates directly to ERPNext's native mapper. Current certificate posting
creates native invoices without the former contractor_order flag.

Existing historical certificate APIs that depended on removed invoice custom tables
are retained as source, but their former invoice form extensions are not restored.
Use the current clause clearance accounting flow for new postings.

Deploy with the usual site migration, app asset build, cache clear, restart, and
browser hard refresh. Verify native document creation and current clearance invoice
posting on a test site after migration. Local tests cannot inspect site-only custom
fields, scripts, or active workflows.


### Purchasing naming exception

Purchase Order and Purchase Receipt require a selected Project with a nonblank
Project Abbreviation. Their only overridden controller method is autoname. Counters
are separate per prefix/Project abbreviation. Purchase Orders always use PO,
including any older records whose stored custom_type was Contract. The former
Order Type selector is not exported and is removed by the naming/standard-document
migrations without dropping its stored SQL values. Existing document names are not
renamed. Native warehouse handling and all other transaction behavior remain in use.
