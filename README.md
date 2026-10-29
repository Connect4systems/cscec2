# Contractor App

Contracting workflows for Frappe/ERPNext, including tender analysis, BOQ
costing, project contracts, budgets, and subcontract clearances.

See [the user guide](docs/user-guide/README.md) for workflow documentation.

## Local checks

Install the Python dependencies before running the standalone regression suite:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Run the JavaScript regression checks with Node.js installed:

```powershell
node --test tests/*.test.js
```

These checks use framework stubs. Full migration, permissions, accounting, and
browser validation require a configured Frappe/ERPNext Bench site with this app
installed; the standalone suite does not replace those integration checks.
