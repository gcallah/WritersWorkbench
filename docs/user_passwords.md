# User passwords (issue #3)

This extends Blessing's `users/query.py` rather than introducing a duplicate
`users.py`. The existing function names, IDs and return types are preserved.

## Endpoint handoff

- `add({"name": ..., "auth_key": ..., "password": ...})` now requires all
  three values to be non-empty strings. Missing/invalid fields raise ValueError.
- Pass the password as supplied; this module hashes it with Werkzeug's salted
  scrypt default. Only `password_hash` is stored, never the supplied password.
  Do not send `password_hash` to add/update; the module rejects it.
- `update(id, {"name": ...})` still works without a password.
- `update(id, {"password": ...})` sets or replaces the password hash.
- `check_password(id, password)` returns a boolean. An unknown user or an old
  record without a password hash returns False. Database failures still raise.
- `fetch_by_key`, `fetch_list` and `fetch_dict` omit password and password_hash.
  Existing auth_key behavior is unchanged. Endpoints still need authorization
  and should not expose auth keys in public responses.

Existing records are not deleted or given a default password. They remain
readable, editable and deletable. They need an authorized password-setting or
reset flow before password login will work. This change does not implement that
HTTP flow, issue tokens, change the editor login or replace BackEndCore's own
user endpoints. Eric's #2 endpoints must enforce authorization for user changes,
particularly password changes, and handle validation errors as client errors.

Passwords are not trimmed or logged. Whitespace-only values are rejected; other
leading/trailing spaces are preserved. No additional password policy is imposed
in this task. Existing user-creation callers must now provide a password.

## Tests

`make all_tests` now runs server, projects and users tests, including legacy
records, required passwords, hashing, verification, replacement, hidden hashes
and invalid input. Use the usual activated virtual environment and repository
root in PYTHONPATH. The make recipe sets TEST_DB and the test SQLite filename.

Reference: https://werkzeug.palletsprojects.com/en/stable/utils/#module-werkzeug.security

## SQLite compatibility and existing data

The old collection name `Users` collides with BackEndCore's `users` login table
because SQLite ignores case in table names and the adapter ignores the DB name.
The application user store now uses `WorkbenchUsers` (on both database backends).
This keeps the two user models separate without modifying BackEndCore.

If you have application users in the old `Users` store, back up your database,
stop the API server, select the same database settings used by your application,
and run `python -m users.migrate_legacy` once before restarting the server.
For the default local SQLite configuration, from the repository root:

```bash
source .venv/bin/activate
export PYTHONPATH="$PWD"
export DATABASE=sqlite
export SQLITE_LOC="$PWD/database"
unset TEST_DB SQL_DB_NM
python -m users.migrate_legacy
```

The importer preserves IDs, names and auth keys, skips unrelated BackEndCore
login records, retains the source and never overwrites an existing destination
record. Imported users have no password until an authorized update sets one.
Do not rerun this importer after deleting imported users: the retained originals
would be imported again. A new installation needs no import. These users remain
separate from BackEndCore login accounts; this task does not link those systems.
