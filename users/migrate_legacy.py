"""Explicit, non-destructive import of the old WritersWorkbench Users store.

Run once after backing up an existing database: python -m users.migrate_legacy
Source records remain. Do not rerun after deleting imported users.
"""
import backendcore.data.db_connect as dbc
from users import query as qry


def migrate():
    """Copy old application users with their IDs; never overwrite records."""
    # SQLite may reflect the colliding table as users rather than Users.
    sources = ['Users']
    if dbc.db_type in ('sqlite', 'sqlite_mem'):
        sources.append('users')
    copied = 0
    qry.fetch_list()
    cache = qry.get_cache(qry.COLLECT)
    for source in sources:
        for record in dbc.fetch_all(qry.DB, source, no_id=True):
            # BackEndCore login accounts have a different schema. Leave alone.
            if not all(isinstance(record.get(fld), str)
                       and record[fld].strip()
                       for fld in (qry.ID, qry.NAME, qry.AUTH_KEY)):
                continue
            user_id = record[qry.ID]
            if cache.fetch_by_key(user_id) is not None:
                continue
            # Old application records have no password. Never invent one.
            user = {fld: record[fld]
                    for fld in (qry.ID, qry.NAME, qry.AUTH_KEY)}
            cache.add(user)
            copied += 1
    return copied


if __name__ == '__main__':
    print(f'Imported {migrate()} legacy users; source records retained.')
