# Tender Analysis

Tender Analysis is the clause-based tender workflow. Opportunity keeps its standard
ERPNext item behavior. Existing Opportunity custom grouping data is retained but
hidden; existing tenders are not automatically converted.

## Workflow

1. Open **Tender > Tender** (Tender Analysis), fill the tender number, party,
   company, currency, and title.
2. Add group headings and detail clauses in their desired order. Enter title,
   quantity, and UOM in the table. Detail quantities must be positive.
3. Save. Automatic numbering regenerates `1`, `1_1`, `1_2`, `2`, `2_1` on every
   save. Groups must precede details. Rates and amounts are maintained by pricing;
   group amounts are summaries and are excluded from the grand total.
4. Alternatively, download **Excel Template**, fill it, save the tender, and use
   **Upload Excel**. Review the preview and click **Apply Rows** to replace the
   current table. Excel uses `.xlsx`, literal values, and the exact template
   headers. Set Is Group to 1 or 0. Series values must be unique and match the
   preceding group; gaps are allowed. Imported rows use **From Excel** numbering,
   preserving the spreadsheet series on save. Switch to Automatic to renumber.
   Replacement is available only before creating Contractual Clause documents.
5. Click **Create Contractual Clauses**. This creates one document per row, linked
   to the tender, and writes its reference into the table. Repeated clicks create
   only missing clauses. A created clause's group type cannot be changed; its
   title follows the tender row. Repeated titles are supported.
6. Click **Create > Costing Note**, then save the draft. Source rows and quantities
   are fixed to the tender. If quantities or the clause structure change, recreate
   the draft Costing Note. References use row IDs, never titles or series numbers.
7. Use each detail row's **BOQ** button, fill unit resource costs, and submit the
   BOQ. BOQ total unit cost returns to the matching Costing Note row. Existing
   resource tables continue to use actual Items for materials, labor, etc.; the
   clause replaces the Item being priced at the BOQ header.
8. Set profit margins and save. Total cost = unit cost × quantity. Selling amount
   = total cost × (1 + margin / 100). Group rows aggregate detail prices.
9. Submit the Costing Note to write selling rates and amounts to Tender Analysis.
   Only one applied Costing Note may own a clause's prices at a time.
10. To reprice, cancel the Costing Note first. Its previous tender rates are
    restored, without subtracting arbitrary amounts. Submitted BOQs remain as an
    audit trail and may then be cancelled. Create a new Costing Note for revised
    pricing. Applied clauses cannot be deleted or have quantities changed until
    their Costing Note is cancelled.

New document permissions initially follow this app's existing **System Manager**
policy. Grant additional role permissions through Role Permission Manager as needed.

## Deployment

After these repository changes have been pushed and pulled on the server:

```bash
cd ~/frappe-bench
bench --site actual-site-name backup
./env/bin/pip install -e apps/contractor
bench --site actual-site-name migrate
bench build --app contractor
bench restart
```

The migration hides legacy Opportunity grouping fields and removes only the
Opportunity Item Property Setters previously shipped by this app. It retains all
stored values. Other Opportunity custom fields, including tender attachments,
remain available. Sales Order, Purchase Order, and Project pricing paths remain.

Local checks:

```bash
python -m unittest discover -s tests -v
```

Live validation on a Frappe site must cover Excel upload, clause generation twice,
BOQ submission/cancellation, Costing Note submission/cancellation, permissions,
and standard Opportunity creation after migration.

## Project Contracts

After every active Costing Note is submitted and each detail clause has applied
pricing, **Create > Project Contract** appears on the Tender Analysis. Cancelled
Costing Notes do not block creation; a draft Costing Note does. The server checks
these conditions again when creating, saving, and submitting the contract.

The new document copies the tender company, currency, clauses, numbering,
quantities, UOM, selling rates, Costing Note references, and submitted BOQ links.
**Contractor Order** is always checked. Tender Analysis's Connections tab and the
Tender workspace include Project Contracts. One active contract is allowed per
tender; cancelled contracts can be replaced or amended.

Complete Customer (required when the tender party is a Lead or Prospect), delivery
date, addresses, contact, customer purchase order, payment terms, and terms and
conditions. For a foreign-currency contract enter its conversion rate. Clause
quantities and rates can be adjusted for the commercial agreement; source clause
identities and series remain tied to the tender. Group rows are summaries.

Select **Sales Taxes and Charges Template** in Taxes and Totals. The company default
template is loaded when creating a contract. Templates are filtered by company and
disabled status. The standard ERPNext **Sales Taxes and Charges** table supports
Actual, On Net Total, On Previous Row Amount, On Previous Row Total, On Item Quantity,
and included-in-rate taxes. The installed ERPNext Sales Order tax engine calculates
these values in an unsaved context, with only detail clauses as calculation rows;
no stock Items or Sales Orders are created. Totals recalculate in draft forms and
are calculated again by the server on save/submit. Standard discount basis,
percentage/amount discounts, currency precision, and rounded totals are supported.

Contracting uses the Selling Deductions Template and shared Deductions table,
including an editable **Title** on each deduction row. Titles are copied from the
template; account name is a default when the title is empty. Deductions apply to
the calculated grand total and determine net payable. The Advance Payment Discount
and Business Guarantee Insurance Deduction Rate fields and their Project Contract
validation have been removed. Company no longer displays this app's contractor
account settings, and this app no longer exports Company fields owned by HRMS or
other apps. Stored historical Company settings and contract percentage values are
preserved; HR/payroll and loan fields remain under their owning apps.

It is a standalone commercial contract: stock fulfillment and invoicing
continue through standard ERPNext documents. It does not post accounting entries.

Sales Order now uses its standard ERPNext client controller and item table. The
app's custom group filters, numbering, Project/Costing Note/Clearence buttons,
contracting custom fields, and exported table Property Setters are retired.
Historical values remain in the database; third-party customizations are retained.
Old Costing Notes no longer change Sales Order prices on submit or cancel.

Before production use, verify the contract action is absent with a draft Costing
Note, visible after submission, copies the correct prices, blocks duplicate active
contracts, and supports save/submit/cancel/amend. Also create a standard Sales Order
after migration and check its Item selector, quantities, rates, and standard actions.

The tax migration copies legacy Project Contract Tax rows to Sales Taxes and Charges
without recalculating historical or submitted totals. Run the native engine checks
on a test site after migration:

```bash
bench --site test-site-name run-tests --doctype "Project Contract"
```

## Project Offers

**Create > Project Offer** on Tender Analysis uses the same completed-costing checks
as Project Contract: all active Costing Notes must be submitted and every detail
clause must have applied pricing. One active offer per tender is allowed. Offers
use `POF-YYYY-00001` numbering and the same tabs, clause fields, taxes, deductions,
terms, totals, and permissions as Project Contract. Their forms and calculation
handlers share one implementation.

After saving and submitting an offer, use **Create > Project Contract**. This copies
the submitted offer's commercial values, including negotiated quantities and rates,
tax settings, deduction titles, addresses, and terms into a new draft contract.
The contract stores a read-only **Project Offer** link and retains stable tender row,
Contractual Clause, Costing Note, and BOQ references. Child rows receive new database
identities. The offer's submitted status is checked again on the server.

Repeated conversion opens the existing contract for that offer. An active contract
from another source blocks conversion, maintaining one active contract per tender.
Cancel or delete any active linked contract before cancelling its source offer.
Offers are also available through Tender Analysis Connections and the Tender
workspace. The existing direct Create Project Contract action remains available.

Deploy with the usual site migration, asset build, and restart. Verify both forms'
shared tabs and tax calculations, offer save/submit/cancel/amend, submitted-only
conversion, and the offer-to-contract references on a test site.

## Tender contracting details

Tender Analysis includes a **Contracting** tab with **Selling Deductions Template**,
an editable Deductions table (Title, Account, Percent), Total Deductions, and Net
Payable. Selecting a template populates its rows; users can then edit or add rows.
Tender deduction values are calculated against its Total Amount. Saving also
checks account company, percentage limits, and total deductions.

Creating either Project Offer or Project Contract from the tender copies the
selected template and the current deduction rows, including manual changes. A
contract created from an offer copies the offer's current deduction details.
Each stage is an independent document: editing deductions on a later draft does
not update its source or its template. Calculated values use each document's own
total (Tender Analysis Total Amount; Offer/Contract Grand Total including taxes).
Normal submit/cancel/amend rules apply to submitted offers and contracts.

The migration initializes Net Payable for existing tenders without deduction rows
without resaving them or changing pricing.

## Standard Quotations

Quotation now uses its standard ERPNext form and Items table. The app's item-group
filters, parent inheritance, series numbering, and custom validation are removed.
The migration hides this app's four legacy Quotation Item grouping fields and
removes its three exported column Property Setters. Historical field values remain
stored, and customizations belonging to other apps are preserved. After migrating,
building assets, and restarting, refresh the browser and verify the standard Item
selector, row order, quantities, pricing, taxes, and standard Quotation actions.

## Project names and operational Projects

**Project** is a plain Data field on Tender Analysis, Costing Note, BOQ, Project
Offer, and Project Contract. Tender-to-note, note-to-BOQ, tender-to-offer/contract,
and offer-to-contract mappings copy this text. Editing a later document does not
rename a Project or update its source documents.

Enter the desired name before submitting a Project Contract. Submission creates
an ERPNext Project with that **Project Name**, the standard Project naming series,
company, customer, and expected start/end dates. Project creation permissions are
required. A read-only **Created Project** link on the contract opens the result.
Repeated requests reuse that contract's Project; an unrelated Project with the
same name blocks creation rather than being overwritten.

The Project's **Project Clauses** tab contains two read-only quantity tables:
clause details and a summary by group and unit of measure. Details retain headings,
series, contractual quantities, delivery dates, and tender/Costing Note/BOQ references.
Each table shows customer and subcontractor executed quantities, remaining quantities,
and completion percentages separately. No rate or amount fields are exposed in the
Project clause tables. New snapshots do not copy prices. Historical database columns
are retained for preservation. Prices remain on commercial documents and certificates.
Legacy item-based pricing buttons are not shown on these clause-based Projects.

Older submitted contracts are not bulk-created during migration. Fill and save
their Project text to create the Project, or use **Create > Project** if the name
was already entered. Once a Project exists, the contract's Project text is locked.
To cancel a contract, first set its linked Project status to Cancelled.

The migration preserves existing Project relationships on legacy Costing Notes in
a separate hidden **Source Project** link and converts old link IDs in visible
Project fields to their display names. Operational Project records and historical
contract clauses are preserved.

### Repairing missing Project fields or names

The repair migration force-reloads the relevant DocTypes even if site-edited
metadata has newer timestamps. It clears conflicting Project field Property Setters,
retains customized field ordering, inserts missing Project fields into that order,
and updates metadata cache versions. Blank existing document values are filled
from their source without overwriting manual names or repricing submitted documents.

Opening or saving an existing Costing Note, BOQ, Offer, or Contract with a blank
Project also fetches the source name. Save the fetched value when prompted. For an
older submitted contract without a generated Project, use **Create > Project**;
this resolves the source name if necessary and stores both the name and Project
reference. Existing contracts are not bulk-submitted again or bulk-created during
migration. New contract submissions create the Project in the same transaction,
or return a permission/validation error.

## Connection dashboards

Costing Note Connections includes Tender Analysis under Sources and BOQ under
Pricing. Its explicit `costing_note` dashboard key enables native badge counts and
filters the BOQ list by the actual BOQ parent reference, including documents whose
row link was previously missing.

Project Offer Connections shows Tender Analysis and the distinct Costing Notes
referenced by its clauses, plus downstream Project Contracts. Project Contract
Connections shows Tender Analysis, its source Project Offer, distinct Costing Notes,
and the generated Project. Upstream references use native internal links, so their
badges open the referenced records rather than filtering on unrelated field names.

The connection repair migration refreshes affected metadata and repairs BOQ parent
and row links only where the stored source row or clause gives an unambiguous
match. It rebuilds row navigation references without saving or repricing documents.
After deployment, migrate, build assets, clear the site cache, restart, and refresh
the browser. The native connection check can be run on a test site with:

```bash
bench --site test-site-name run-tests --module contractor.contractor_app.doctype.costing_note.test_connections_native
```

## Subcontractor contract requests (CR)

CR supports Supplier selection and a Contract Clauses table. Add group headings
and detail rows manually; Automatic numbering uses the same `1`, `1_1`, `1_2`
series as Tender Analysis. Detail quantities must be positive, and clause-based
requests require a Supplier. Existing attachment-only requests remain supported.

Save a draft CR, then use **Excel Template** and **Upload Excel** to preview and
replace its clauses using the Tender Analysis spreadsheet format. **From Excel**
preserves valid series and gaps; Automatic renumbers on save.
**Fetch from Project** replaces the table with the selected Project's clauses,
including quantities, UOM, original series, and source references. Select the
Supplier before applying rows. Replacement actions are restricted to drafts.
Fetched references are checked against the selected Project on save.

Deploy with `bench --site actual-site-name migrate`, `bench build --app contractor`,
and `bench restart`. Verify CR manual entry, Excel preview/apply, Project fetch,
and submission on a test site.

## Project Budget and BOQ quantity basis

Project Contract now provides **Create > Project Budget** after submission. The
budget snapshots costs from its exact submitted Costing Note/BOQ references and
uses final contract quantities. Its Total Budget and Contract Clauses Budget tabs
show all five resource categories, including Equipment, with group summaries and
source links. See [Project Budget](project-budget.md) for validation and deployment.

New/draft BOQ resource rows calculate full Project Quantities from editable
quantity-per-clause-unit coefficients. Costing Note and Tender Analysis normalize
unit prices and multiply by clause quantity once. Project Budget uses those same
normalized costs. Existing submitted BOQs retain their historical unit basis and
are not bulk repriced during migration.
