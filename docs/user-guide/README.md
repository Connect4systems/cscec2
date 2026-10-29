# Contractor App user guides / أدلة مستخدم تطبيق المقاولات

Prepared on 29 October 2026 for `https://en.connect4systems.com`.

## Download / التنزيل

- [الدليل العربي PDF](downloads/Contractor-User-Guide-AR.pdf)
- [الدليل العربي Word](downloads/Contractor-User-Guide-AR.docx)
- [English PDF guide](downloads/Contractor-User-Guide-EN.pdf)
- [English Word guide](downloads/Contractor-User-Guide-EN.docx)
- [All guides and screenshots / جميع الأدلة والصور](downloads/Contractor-User-Guides-AR-EN.zip)

Each language includes 22 chapters covering setup, Tender Analysis, Costing Note,
BOQ and equipment, offers/contracts, cost-based Project Budget, progress, CR clause
selection, subcontracting, certificates, taxes/deductions, accounting, retained
supporting documents, standard purchasing, corrections and troubleshooting.

The PDF files are suitable for reading and printing. Word files are editable.
The HTML versions work offline when the supplied `assets` directory remains next
to `downloads`, as in the ZIP. Screenshots show the actual English site interface;
Arabic instructions retain English labels to help users find controls.

## Review scope / نطاق المراجعة

The site was accessed with the user's authorization. Screenshots are actual site
captures, not recreated interfaces. The review used existing records, unsaved
browser examples, and temporary CR drafts deleted after clause-fetch testing.
No financial certificates/invoices were created or submitted. Existing business
records were not edited. Temporary draft creation may advance the naming series.

See [site verification](site-verification.md) for test evidence and limits.
The guides contain existing test-record screenshots and are intended for internal
training. Credentials and authenticated browser sessions are excluded.

## Maintenance

`guide_content.py` contains the paired Arabic/English instructions.
`build_guides.py` generates DOCX, HTML, PDF and ZIP files. It requires `python-docx`,
`playwright`, and Microsoft Edge at the configured local path. Capture helpers
use a temporary authenticated session outside this repository and do not contain
credentials. Browser checks are separate from native Frappe accounting tests.

```powershell
python docs/user-guide/build_guides.py
```
