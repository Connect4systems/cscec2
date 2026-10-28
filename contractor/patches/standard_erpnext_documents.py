"""Remove this app's extensions from native ERPNext trading forms."""
from contractor.standard_documents import restore_standard_documents


def execute():
    result = restore_standard_documents()
    print('Restored standard ERPNext documents: ' + ', '.join(
        f'{key}={len(result[key])}' for key in ('removed_fields', 'removed_setters', 'removed_links')))
