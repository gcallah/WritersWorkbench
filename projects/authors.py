"""
Authors, stored through BackEndCore.
Authors are joined to projects through the author_project join table.
"""
from uuid import uuid4

from backendcore.data.caching import get_cache, needs_cache

from projects import query

COLLECT = 'Authors'

# Field names:
ID = 'id'
NAME = 'name'

MAX_NAME_LEN = 200


def needs_authors_cache(fn):
    """
    Should be used to decorate any function that uses datacollection methods.
    """
    return needs_cache(fn, COLLECT, query.DB, COLLECT, key_fld=ID)


def check_name(name):
    if (not isinstance(name, str) or not name.strip()
            or len(name) > MAX_NAME_LEN):
        raise ValueError(f'Author {NAME} must be 1 to {MAX_NAME_LEN} '
                         + 'characters.')


def is_valid(author_id):
    return fetch_by_key(author_id) is not None


@needs_authors_cache
def add(name):
    """
    Create an author with this name; returns the new author's id.
    """
    check_name(name)
    author_id = uuid4().hex
    get_cache(COLLECT).add({ID: author_id, NAME: name.strip()})
    return author_id


@needs_authors_cache
def fetch_by_key(author_id):
    """
    Get a single author by id, or None when absent.
    """
    return get_cache(COLLECT).fetch_by_key(author_id)


@needs_authors_cache
def fetch_dict():
    """
    Fetch all authors: returns a dict keyed by author id.
    """
    return get_cache(COLLECT).fetch_dict()


@needs_authors_cache
def fetch_by_name(name):
    """
    Get all authors with this exact name: returns a dict keyed by id.
    """
    check_name(name)
    return get_cache(COLLECT).fetch_by_fld_val(NAME, name.strip())


@needs_authors_cache
def update(author_id, name):
    """
    Rename the author with this id.
    """
    check_name(name)
    if not is_valid(author_id):
        raise ValueError(f'No author with {ID} {author_id}')
    return get_cache(COLLECT).update(author_id, {NAME: name.strip()})


@needs_authors_cache
def delete(author_id):
    if not is_valid(author_id):
        raise ValueError(f'No author with {ID} {author_id}')
    # Imported here: author_project imports this module.
    from projects import author_project
    author_project.delete_author_links(author_id)
    return get_cache(COLLECT).delete(author_id)


TEST_NAME = 'Test Author'
