"""
This is our interface to user data.
Every user has a unique id, a name, and an auth_key.
"""
from uuid import uuid4

from backendcore.data.caching import needs_cache, get_cache

DB = 'usersDB'
COLLECT = 'Users'

# Field names:
ID = 'id'
NAME = 'name'
AUTH_KEY = 'auth_key'

REQUIRED_FLDS = [NAME, AUTH_KEY]


def needs_users_cache(fn):
    """
    Decorate any function that uses datacollection methods.
    """
    return needs_cache(fn, COLLECT, DB, COLLECT, key_fld=ID)


def _check_fld(fld_nm, val):
    if not isinstance(val, str) or not val.strip():
        raise ValueError(f'User {fld_nm} must be a non-empty string.')


def is_valid(user_id):
    return fetch_by_key(user_id) is not None


@needs_users_cache
def add(user: dict):
    """
    Create a user. Name and auth_key are required.
    A unique id is generated for the user and returned.
    """
    for fld_nm in REQUIRED_FLDS:
        _check_fld(fld_nm, user.get(fld_nm))
    user = dict(user)
    user[ID] = uuid4().hex
    get_cache(COLLECT).add(user)
    return user[ID]


@needs_users_cache
def fetch_by_key(user_id):
    """
    Get a single user by id; returns None if there is no such user.
    """
    return get_cache(COLLECT).fetch_by_key(user_id)


@needs_users_cache
def fetch_list():
    """
    Fetch all users: returns a list.
    """
    return get_cache(COLLECT).fetch_list()


@needs_users_cache
def fetch_dict():
    """
    Fetch all users: returns a dict keyed by id.
    """
    return get_cache(COLLECT).fetch_dict()


@needs_users_cache
def update(user_id, update_dict: dict):
    """
    Update the fields in update_dict for this user. The id can't change.
    """
    if ID in update_dict:
        raise ValueError(f'User {ID} can not be updated.')
    for fld_nm in REQUIRED_FLDS:
        if fld_nm in update_dict:
            _check_fld(fld_nm, update_dict[fld_nm])
    if fetch_by_key(user_id) is None:
        raise ValueError(f'No user with id {user_id}')
    return get_cache(COLLECT).update(user_id, update_dict)


@needs_users_cache
def delete(user_id):
    if fetch_by_key(user_id) is None:
        raise ValueError(f'No user with id {user_id}')
    return get_cache(COLLECT).delete(user_id)


TEST_SAMPLE = {
    NAME: 'Test User',
    AUTH_KEY: 'test-auth-key',
}
