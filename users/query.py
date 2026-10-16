"""User CRUD. New users require a password; old records remain readable."""
from uuid import uuid4

from werkzeug.security import generate_password_hash, check_password_hash
from backendcore.data.caching import needs_cache, get_cache

DB = 'usersDB'
# SQLite table names are case-insensitive; BackEndCore already uses users.
COLLECT = 'WorkbenchUsers'

ID = 'id'
NAME = 'name'
AUTH_KEY = 'auth_key'
PASSWORD = 'password'
PASSWORD_HASH = 'password_hash'

REQUIRED_FLDS = [NAME, AUTH_KEY, PASSWORD]


def needs_users_cache(fn):
    """Decorate any function that uses datacollection methods."""
    return needs_cache(fn, COLLECT, DB, COLLECT, key_fld=ID)


def _check_fld(fld_nm, val):
    if not isinstance(val, str) or not val.strip():
        raise ValueError(f'User {fld_nm} must be a non-empty string.')


def _prepare(fields):
    """Copy input and replace a supplied password with its salted hash."""
    if PASSWORD_HASH in fields:
        raise ValueError('Supply password, not password_hash.')
    result = dict(fields)
    if PASSWORD in result:
        result[PASSWORD_HASH] = generate_password_hash(result.pop(PASSWORD))
    return result


def _without_password(user):
    """Return a copy without password fields, never modify the cache."""
    if user is None:
        return None
    return {key: value for key, value in user.items()
            if key not in (PASSWORD, PASSWORD_HASH)}


def is_valid(user_id):
    return fetch_by_key(user_id) is not None


@needs_users_cache
def add(user: dict):
    """Create a user with name, auth_key and password; return its new id."""
    for fld_nm in REQUIRED_FLDS:
        _check_fld(fld_nm, user.get(fld_nm))
    user = _prepare(user)
    user_id = uuid4().hex
    user[ID] = user_id
    get_cache(COLLECT).add(user)
    return user_id


@needs_users_cache
def fetch_by_key(user_id):
    """Return a user without password fields, or None when absent."""
    return _without_password(get_cache(COLLECT).fetch_by_key(user_id))


@needs_users_cache
def fetch_list():
    """Return all users without password fields."""
    return [_without_password(user)
            for user in get_cache(COLLECT).fetch_list()]


@needs_users_cache
def fetch_dict():
    """Return users keyed by id, without password fields."""
    return {key: _without_password(user)
            for key, user in get_cache(COLLECT).fetch_dict().items()}


@needs_users_cache
def update(user_id, update_dict: dict):
    """Update supplied fields. Password is required only when changing it."""
    if ID in update_dict:
        raise ValueError(f'User {ID} can not be updated.')
    for fld_nm in REQUIRED_FLDS:
        if fld_nm in update_dict:
            _check_fld(fld_nm, update_dict[fld_nm])
    if fetch_by_key(user_id) is None:
        raise ValueError(f'No user with id {user_id}')
    return get_cache(COLLECT).update(user_id, _prepare(update_dict))


@needs_users_cache
def check_password(user_id, password):
    """Check a password. Missing users or legacy hashes never authenticate."""
    if not isinstance(password, str) or not password.strip():
        return False
    user = get_cache(COLLECT).fetch_by_key(user_id)
    if user is None:
        return False
    stored_hash = user.get(PASSWORD_HASH)
    if not isinstance(stored_hash, str) or not stored_hash:
        return False
    try:
        return check_password_hash(stored_hash, password)
    except (ValueError, TypeError):
        return False


@needs_users_cache
def delete(user_id):
    if fetch_by_key(user_id) is None:
        raise ValueError(f'No user with id {user_id}')
    return get_cache(COLLECT).delete(user_id)


TEST_SAMPLE = {
    NAME: 'Test User',
    AUTH_KEY: 'test-auth-key',
    PASSWORD: 'test-only-password',
}
