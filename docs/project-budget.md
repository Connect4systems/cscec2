# Project Budget and full-project BOQ quantities

From a submitted **Project Contract**, use **Create > Project Budget**. The action
opens a new unsaved draft. An existing active budget for that contract is opened
instead. One draft/submitted budget is allowed per contract; cancelled budgets can
be amended or replaced. Saving takes a contract lock and checks uniqueness again.

The operational Project must already exist and belong to the contract. Each detail
clause must have an exact source Tender Analysis row, a submitted matching Costing
Note row, and a submitted BOQ linked to that row. Company, currency, clause identity,
and UOM are checked. Source matching uses database row references, never titles or
series numbers. Missing or ambiguous sources stop creation. Multiple source Costing
Notes are supported. The sources must be readable and the user must have permission
to create Project Budget.

## Budget form

- Details: Project Contract, operational Project, Tender Analysis, Company, Currency,
  Budget Date, status, and title. Names use PBG-YYYY-00001.
- **Total Budget**: Total Project Budget, Total Material, Total Labour,
  Total Subcontractor, Total Other Expenses, and Total Equipment.
- **Contract Clauses Budget**: group/series/title, final contract quantity and UOM,
  BOQ unit cost and total clause budget. Open a row for the category breakdown and
  Contractual Clause/Costing Note/BOQ links. Source row IDs are retained invisibly.
- Connections: the contract, Project, tender, distinct Costing Notes, and BOQs.
  Project Contract also lists its budgets in Connections; Tender workspace has a
  Project Budget shortcut.

All source-derived values are read-only, recalculated/verified by the server, and
exclude selling profit, taxes, and deductions. Group headings summarize their detail
rows but do not count again in the budget grand total. Every contract clause is
included, and the contract row order/series are preserved. Budgets do not post stock
or accounting transactions. The custom budget does not extend ERPNext's standard
Budget or native sales/purchase transaction forms.

The calculation uses **final Project Contract quantities**, which may differ from
the tender quantities. Each detail budget is quantity times the normalized BOQ unit
cost. Category amounts are rounded to the document's currency precision; rounding
residuals are allocated across the categories so their sum matches the clause total.
Equipment is included separately rather than lost in reconciliation.

A saved draft rejects changed source identities, quantities, or unit costs rather
than silently adopting different pricing. Submitted budgets are snapshots and use
standard submit/cancel/amend rules. Cancel/delete active budgets before cancelling
their Project Contract. Native links protect submitted budget references to source
Costing Notes and BOQs as well. Amendments/replacements must still have valid sources.

## BOQ quantities and pricing

New BOQs and saved/converted drafts use **Quantity Basis = Project Quantity**.
For each material, labour, subcontractor, and expense row:

```
Resource Project Quantity = Quantity per Clause Unit * BOQ Project Quantity
Resource Total Cost       = Resource Project Quantity * Resource Rate
BOQ Total Project Cost    = sum(resource Total Costs)
Cost per Clause Unit      = BOQ Total Project Cost / BOQ Project Quantity
```

The quantity-per-unit coefficient is editable. The calculated Project Quantity and
row total are read-only in the BOQ form. Changing Project Quantity recalculates from
the coefficient, so repeated saves/recalculations do not multiply quantities again.
The server repeats these calculations and rejects nonfinite/negative inputs and
nonpositive Project Quantity. Tender-linked BOQs take Project Quantity from their
Costing Note clause, preventing stale or tampered header quantities.

Template BOQ quantities remain coefficients per clause unit. The shared resource
controls keep template Qty editable and hide the Project coefficient column there.
Applying a template copies its coefficient and scales it to the BOQ Project Quantity.
If a site already has a custom_equipment table on BOQ, the migration supplies its
missing coefficient field and equipment subtotal where needed, and the same quantity
calculation includes that table.

Submitted project-basis BOQs return their normalized **unit cost** to Costing Note.
Costing Note multiplies it by its clause quantity once, applies the margin, and
submits the unit selling rate to Tender Analysis. Tender detail amounts continue to
be quantity times that selling rate. Project Budget normalizes the same BOQ category
costs and scales them to the final contract quantity once.

Example:

| Stage | Value |
| --- | ---: |
| BOQ Project Quantity | 100 |
| BOQ total resource costs | 2,300 |
| Normalized clause unit cost | 23 |
| Costing Note total cost for quantity 100 | 2,300 |
| Selling amount with 10% margin | 2,530 |
| Tender selling rate | 25.30 |
| Budget when final contract quantity is 150 | 3,450 |

## Historical records and deployment

The migration marks existing unclassified BOQs as **Per Unit** and adds display
fields for unit/project totals without modifying their stored original resource
quantities, total_cost, submitted status, or applied tender prices. Opening/saving a
draft converts its old Qty coefficients into per_unit_qty and calculates project
quantities. Existing submitted/cancelled BOQs retain their historical basis. Budget
and pricing normalization support both modes, so legacy unit-based BOQs still work.

No historical contracts, approved budgets, or submitted pricing documents are bulk
resaved or repriced during migration. New fields/DocTypes and the contract/workspace
metadata are force-reloaded to avoid stale form metadata.

Deploy all changed/new files, then:

```bash
bench --site en.connect4systems.com migrate
bench build --app contractor
bench --site en.connect4systems.com clear-cache
bench restart
```

Hard-refresh the browser. Local checks cover arithmetic, source identity/status,
uniqueness, snapshot tampering, Project quantity scaling, legacy basis handling,
tender propagation, template isolation, and button routing. Native metadata checks
are provided for a migrated test site:

```bash
bench --site test-site-name run-tests --doctype "Project Budget"
```

Also verify real permissions, draft/save/submit/cancel/amend, two concurrent budget
creations, missing/cancelled sources, template import, existing submitted BOQ display,
and Project Contract cancellation on that site. Local tests use a mocked Frappe
boundary and do not prove native-site migration or workflow behavior.
