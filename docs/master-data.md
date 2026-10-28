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
switching groups. **Insert Clauses** replaces the current CR clause table, includes
the selected details' headings once, and preserves source ordering and series.
The server checks draft/write permissions, Project read access, selection membership,
and that the CR's Project has not changed while the picker was open.
