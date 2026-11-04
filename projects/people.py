"""
The People table, stored through BackEndCore.

Everyone involved in a project lives here, whatever they do: authors,
editors, copy editors and referees. A person can have more than one
role (for example, an author who also referees). People are joined to
projects through the person_project join table, which also records the
role they have on each project.
"""
from uuid import uuid4

from backendcore.data.caching import get_cache, needs_cache

from projects import query

COLLECT = 'People'

# Field names:
ID = 'id'
NAME = 'name'
ROLES = 'roles'

# Roles:
AUTHOR = 'author'
EDITOR = 'editor'
COPY_EDITOR = 'copy editor'
REFEREE = 'referee'
ALL_ROLES = (AUTHOR, EDITOR, COPY_EDITOR, REFEREE)

MAX_NAME_LEN = 200


def needs_people_cache(fn):
    """
    Should be used to decorate any function that uses datacollection methods.
    """
    return needs_cache(fn, COLLECT, query.DB, COLLECT, key_fld=ID)


def check_name(name):
    if (not isinstance(name, str) or not name.strip()
            or len(name) > MAX_NAME_LEN):
        raise ValueError(f'Person {NAME} must be 1 to {MAX_NAME_LEN} '
                         + 'characters.')


def check_role(role):
    if role not in ALL_ROLES:
        raise ValueError(f'Role must be one of: {", ".join(ALL_ROLES)}.')


def clean_roles(roles):
    """
    Check a list of roles and return it with any repeats removed.
    Everyone must have at least one role.
    """
    if not isinstance(roles, list) or not roles:
        raise ValueError('A person needs a list of at least one role.')
    for role in roles:
        check_role(role)
    return list(dict.fromkeys(roles))


def has_role(person, role):
    """
    Takes a person record (not an id).
    """
    return role in person.get(ROLES, [])


def is_valid(person_id):
    return fetch_by_key(person_id) is not None


def _check_exists(person_id):
    person = fetch_by_key(person_id)
    if person is None:
        raise ValueError(f'No person with {ID} {person_id}')
    return person


@needs_people_cache
def add(name, roles):
    """
    Create a person with this name and list of roles; returns their id.
    """
    check_name(name)
    roles = clean_roles(roles)
    person_id = uuid4().hex
    get_cache(COLLECT).add({ID: person_id, NAME: name.strip(),
                            ROLES: roles})
    return person_id


@needs_people_cache
def fetch_by_key(person_id):
    """
    Get a single person by id, or None when absent.
    """
    return get_cache(COLLECT).fetch_by_key(person_id)


@needs_people_cache
def fetch_dict():
    """
    Fetch all people: returns a dict keyed by person id.
    """
    return get_cache(COLLECT).fetch_dict()


@needs_people_cache
def fetch_by_name(name):
    """
    Get all people with this exact name: returns a dict keyed by id.
    """
    check_name(name)
    return get_cache(COLLECT).fetch_by_fld_val(NAME, name.strip())


def fetch_by_role(role):
    """
    Get everyone who has this role: returns a dict keyed by id.
    """
    check_role(role)
    return {person_id: person for person_id, person in fetch_dict().items()
            if has_role(person, role)}


@needs_people_cache
def update(person_id, name):
    """
    Rename the person with this id.
    """
    check_name(name)
    _check_exists(person_id)
    return get_cache(COLLECT).update(person_id, {NAME: name.strip()})


@needs_people_cache
def set_roles(person_id, roles):
    """
    Make this person's roles exactly this list. A role they still have on
    a project can't be removed: take them off the project first.
    """
    roles = clean_roles(roles)
    person = _check_exists(person_id)
    removed = set(person.get(ROLES, [])) - set(roles)
    if removed:
        # Imported here: person_project imports this module.
        from projects import person_project
        still_used = removed & person_project.roles_in_use(person_id)
        if still_used:
            raise ValueError(f'Person {person_id} is still a '
                             + f'{", ".join(sorted(still_used))} on a '
                             + 'project.')
    return get_cache(COLLECT).update(person_id, {ROLES: roles})


def add_role(person_id, role):
    """
    Give a person another role. Does nothing if they already have it.
    """
    check_role(role)
    person = _check_exists(person_id)
    if not has_role(person, role):
        set_roles(person_id, person[ROLES] + [role])


def remove_role(person_id, role):
    """
    Take a role away from a person. Their last role can't be removed.
    """
    check_role(role)
    person = _check_exists(person_id)
    if not has_role(person, role):
        raise ValueError(f'Person {person_id} is not a {role}.')
    set_roles(person_id, [r for r in person[ROLES] if r != role])


@needs_people_cache
def delete(person_id):
    _check_exists(person_id)
    # Imported here: person_project imports this module.
    from projects import person_project
    person_project.delete_person_links(person_id)
    return get_cache(COLLECT).delete(person_id)


TEST_NAME = 'Test Person'
TEST_ROLES = [AUTHOR]
