# Division and Cost Code master data

Run `bench --site actual-site-name migrate` after deploying these changes.
The post-sync patches create 32 Division records and import 870 Cost Codes.
Existing records with matching names are preserved, including their descriptions,
parents, and Cost Types. Repeating either seed function does not create duplicates.

Division uses a required Data field `title` as its document name and a Small Text
`description` field. Titles include division numbers to distinguish reserved entries.
The 01-32 list follows the CSI MasterFormat reference published by SpecsIntact:
https://legacy.wbdg.org/tools/specsintact/Help/SIGeneral/CSIMasterFormat.htm

Cost Codes come from the supplied `D:\2026\Cost Code.xlsx` workbook. The bundled
JSON contains its 870 rows, descriptions, parent links, and Cost Type assignments.
Cost Type remains a Cost Center link, matching the existing form and screenshot.
The import uses the Default Company in Global Defaults, falling back to the only
Company when exactly one exists. It reads that Company's abbreviation and creates
`Project Cost - <abbr>` and these leaf Cost Centers:

- Equipments - <abbr>
- Labour - <abbr>
- Material - <abbr>
- Subcontractor - <abbr>

Workbook Cost Type references ending in ` - C` are mapped to the selected Company's
abbreviation. The Cost Type selector supports Project Cost groups for every company.
If several companies exist without a default, set Default Company in Global Defaults
before migration. An explicit company can also be supplied when running manually:

```bash
bench --site actual-site-name execute contractor.master_data.seed_cost_codes --kwargs '{"company": "Your Company Name"}'
```

No accounts or Company records are created. The 254 blank Cost Type values in the
workbook remain blank. The other 616 rows retain their Cost Type categories with the selected Company suffix.
An existing incompatible Cost Center stops the migration with an explanatory error.

The workbook contains invalid tree relationships. The bundled import corrects:

- `03.00.000.000`: remove its parent to make Division 03 a root, breaking its cycle
  with `03.01.000.000`.
- `06.42.001.000`: use Division 06 (`06.00.000.000`) as its parent and mark it as
  a group, breaking its cycle with its Material child.
- `14.20.001.000.M`: mark it as a group because the workbook assigns a child to it.

Cost Code now inherits Frappe's NestedSet controller, maintaining the existing
DocType's tree boundaries when codes are inserted or moved.

Local validation: `python -m unittest discover -s tests -q`.
Live-site validation should check migration, Cost Code tree navigation, the four
Cost Type choices, representative imported rows, and rerunning the import.

CR **Fetch from Project** opens a clause picker. Leave **All Clauses** checked to
fetch the full Project, or uncheck it and choose a **Group Clause**. Tick individual
details or **Select All Clauses in This Group**. Choices remain selected when
switching groups. **Insert Clauses** adds to the existing CR clause table, keeps
existing quantities and edits, and skips already added Project rows. New details
are inserted under their group heading without duplicating headings. Source series
are kept where available; conflicting new series are assigned unused numbers.
The server checks draft/write permissions, Project read access, selection membership,
and that the CR's Project has not changed while the picker was open.

In the CR Project picker, **All Clauses** hides the Group Clause and group-selection
controls. Uncheck it to show both controls. Selecting a group and leaving **Select
All Clauses in This Group** unchecked shows its details with checkboxes and editable
quantities. Checking it selects the whole group and hides the detail table. Quantity
changes are validated as finite positive numbers and apply to CR only; Project
quantities remain unchanged.

## CR, Subcontractor Contract, and Subcontract Clearnce

On a submitted CR, use **Create > Subcontractor Contract**. Native Frappe workflow
approval/submission permissions remain in force; no new workflow is installed.
The new unsaved draft copies the CR's Project, Supplier, Contract Type, dates,
attachments, notes, comparison reference, numbering, and clause values. Child rows
get new identities and retain their source CR row reference. An existing active
contract for that CR is opened on repeated conversion. Saving also checks the
submitted CR, matching Project/Supplier, and one active contract per CR.

Subcontractor Contract can also be created directly. **Attach Contract** is required.
Its clause entry, Excel preview/import, and Project picker share CR's implementation.
Repeated Project fetches add clauses without resetting the table. Enter agreed unit
rates; group amounts and Contract Amount sum the details. Detail rates must be
positive before submission. Company follows the Project, currency defaults to the
company currency, and foreign currencies require a positive conversion rate.

On a submitted contract, use **Create > Subcontract Clearnce**. It opens a new unsaved
certificate with the contract's Supplier, Project, Company, currency, series, clause
references, and agreed rates. Current-period quantities start at zero. Enter the
period quantities and review taxes, deductions, and accounting settings before
submitting. Contract rates are authoritative; certificates cannot substitute rows
from another contract or change the Supplier/Project. Submitted certificates count
toward the contract's cumulative quantities. Fetched Project clauses also retain
the existing Project-wide subcontract quantity cap. Manual/imported contract clauses
use their contract quantities and do not create Project progress rows.

The existing certificate tax/deduction calculations, Purchase Invoice creation,
accounting cancellation, and Project progress refresh remain in use. Cancel or
delete active certificates before cancelling their Subcontractor Contract, and
cancel/delete active contracts before cancelling their CR. Historical attachment-only
contracts remain available; add clauses to a new draft/amendment before using the
new certificate action. Existing contract type names are retained in the master.

Deploy with:

```bash
bench --site en.connect4systems.com migrate
bench build --app contractor
bench --site en.connect4systems.com clear-cache
bench restart
```

Hard-refresh the browser. On a test site, verify workflow approval and submission,
CR conversion twice, direct contract creation, manual/Excel/Project clause entry,
attachment requirements, rates and totals, sequential certificate quantities,
Project-wide quantity limits, taxes/deductions, accounting submission/cancellation,
and cancellation guards. Local tests use mocked Frappe services and do not replace
these native-site checks.
