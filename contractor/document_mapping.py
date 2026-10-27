"""Copy editable child-row values without reusing database identities."""


def copy_child_values(row):
    excluded = {"name", "doctype", "parent", "parentfield", "parenttype", "idx", "docstatus",
        "owner", "creation", "modified", "modified_by"}
    values = dict(row) if isinstance(row, dict) else row.as_dict()
    return {key: value for key, value in values.items()
        if key not in excluded and not key.startswith("_")}
