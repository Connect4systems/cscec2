# App cleanup and retained dependencies

The approved cycle is Tender Analysis → Costing Note/BOQ → Project Offer →
Project Contract → Project → Project Clearnce/Subcontract Clearnce → native
invoices and deduction journals.

The installation definitions for **Contract Type**, **E-Language**, and **Edu**
have been retired: no other shipped schema refers to them. Their small Python
controllers remain so a site's existing records remain readable. On migration,
the cleanup checks the actual site before removing each DocType's metadata.
It preserves definitions with records, external Link/Table fields, connection
links, or native direct/dynamic configuration links. Custom definitions and
definitions owned by another module are preserved. Business rows and SQL tables
are not dropped.

Unused old clearance JavaScript and empty test skeletons have been removed.
Historical item-based calculation and invoice helpers live in `contractor.legacy`.
The original Python API paths remain as compatibility imports for saved client
scripts and historical actions. The current certificate controllers retain the
historical behavior only for records marked `legacy_record`.

The following definitions remain because they are still referenced:

| Definition | Required by |
| --- | --- |
| Contractors table | BOQ and Template BOQ subcontract costing |
| Group Item | Historical Projects, Costing Notes, and certificates |
| Clearence Item | Historical customer certificate rows |
| Purchase Clearence Item | Historical supplier certificate rows |
| Clearence Items Summary | Historical certificate summaries |
| Clearence Type | Historical certificate item type links |

No DocType or feature named **Texture** was found in the repository. The read-only
site audit lists matching DocType names so a site-only customization can be
identified; it does not remove them.

Before migration, use a backed-up test copy of the site to inspect the cleanup:

```bash
bench --site TEST_SITE execute contractor.app_cleanup.audit
bench --site TEST_SITE migrate
bench build --app contractor
bench --site TEST_SITE clear-cache
bench restart
```

Replace TEST_SITE with the test site's name. Migration prints whether each retired
definition was removed or retained and why. The audit command is read-only and can
be rerun afterward. Test opening old certificates and creating new certificates,
and verify that BOQ still includes subcontract costing before production rollout.

Local verification covers the cleanup guards and the app's logic tests. It does
not replace migration and workflow verification against a configured Frappe site.
