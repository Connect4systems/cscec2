# Field audit — 30 October 2026

## Live access result

An unauthenticated Playwright navigation to `https://en.connect4systems.com/app`
returned HTTP 200 and redirected to `/login?redirect-to=%2Fapp#login` with a password
form. The previous temporary authenticated storage file is absent. No attachable
browser debugging endpoint is available for the user's existing signed-in session.
Authenticated forms and deployed fixes have therefore **not** been retested.
No site records or metadata were changed.

## Source findings

| Form / field | Finding | Recommendation |
| --- | --- | --- |
| Costing Note / `group_items` | Legacy Item-based summary table remains visible by schema; tender pricing explicitly empties it. No tender-specific display rule exists in its form script. | Hide for tender notes; retain historical data and legacy behavior until dependencies are migrated. |
| Costing Note Items / `item_group`, `parent_group` | Legacy Item links remain in metadata, conditional on no Tender Analysis. `item_group` is also conditionally mandatory. The current child schema has no `item` or `group_item`, although legacy client/controller paths still reference them. | Review non-tender creation paths before retiring these fields; tender notes should use Contractual Clause and Clause Title. |
| Template BOQ / `item_code` | Header Item Code is required. Tender BOQ template selection deliberately omits this filter. Non-tender BOQ template selection still uses it. | Make optional for clause-based templates after validating the legacy picker. Do not delete existing Item associations. |
| BOQ / `item` | Legacy Contracting Item is retained; refresh already hides it for tender notes. | Confirm live visibility after deployment. Keep until legacy BOQ dependencies are migrated. |
| Costing Note client / removed `item`, `group_item` | Local setup/refresh now guard absent fields; regression test passes. Legacy Item handlers remain for older paths. | Deploy and verify opening an existing tender note and creating/opening its clause BOQ. |

Item links in Material, Labor, Equipment, Contractor and Expense resource rows
represent costing resources and are not established as unwanted by this review.
Hidden source identifiers, previous-pricing fields and BOQ references support
mapping, cancellation and audit history; do not remove them as cosmetic cleanup.

## Remaining live checks

With an authenticated automation session, inspect effective metadata (including
Custom Fields and Property Setters), open existing and new forms, inspect child
row dialogs, and exercise clause/BOQ/template actions without saving transactions.
Compare live fields with the source findings above. Source metadata alone cannot
establish which custom fields are visible on the deployed site.

## Local repairs

- Removed the legacy Group Item summary from Costing Note metadata and its
  summary-building code.
- Removed Item Group and Parent Group from Costing Note Items metadata, along
  with obsolete Item queries, numbering and field handlers in the form script.
- Removed Template BOQ header Item Code and the BOQ template picker filter that
  referenced it. Resource Item links are retained.
- Existing database columns and historical child records are not deleted by
  this patch; fields are removed from the application definitions.
- Registered `contractor.patches.clause_pricing_fields` reloads the three affected
  metadata definitions and clears cache without resaving business documents.
- Validation: 175 Python tests and six JavaScript test files pass, including
  tender/legacy summary visibility and template resource costing without a header Item.

These repairs are local. Deployment, site migration and authenticated UI
verification remain outstanding.
