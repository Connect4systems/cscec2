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
The import requires an existing Company with abbreviation `C` and its root Cost
Center. It creates `Project Cost - C` if missing, then these leaf Cost Centers:

- Equipments - C
- Labour - C
- Material - C
- Subcontractor - C

No accounts or Company records are created. The 254 blank Cost Type values in the
workbook remain blank. The other 616 rows retain their supplied Cost Types.
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
