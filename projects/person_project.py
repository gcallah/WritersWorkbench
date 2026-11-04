"""
The person_project join table: links people to projects, with the role
the person has on that project.

Each row is one (person, project, role). A person can be on many
projects, a project can have many people, and a person can have more
than one role on the same project (one row per role). For example, Ada
can be an author on one project and a referee on another.

Every role someone has on a project is also in their roles in the People
table: linking a person with a role gives them that role if they didn't
have it.
"""
from uuid import uuid4

from backendcore.data.caching import get_cache, needs_cache

from projects import people, query

COLLECT = 'PersonProject'

# Field names:
ID = 'id'
PERSON_ID = 'person_id'
PROJECT_CODE = 'project_code'
ROLE = 'role'


def needs_person_project_cache(fn):
    """
    Should be used to decorate any function that uses datacollection methods.
    """
    return needs_cache(fn, COLLECT, query.DB, COLLECT, key_fld=ID)


def _check_project(project_code):
    if query.fetch_by_key(project_code) is None:
        raise ValueError(f'No project with code {project_code}')


def _check_person(person_id):
    if not people.is_valid(person_id):
        raise ValueError(f'No person with id {person_id}')


@needs_person_project_cache
def _project_rows(project_code):
    return get_cache(COLLECT).fetch_by_fld_val(PROJECT_CODE, project_code)


@needs_person_project_cache
def _person_rows(person_id):
    return get_cache(COLLECT).fetch_by_fld_val(PERSON_ID, person_id)


def _find_link(person_id, project_code, role):
    """
    Returns the id of the row linking this person, project and role,
    or None.
    """
    for row_id, row in _project_rows(project_code).items():
        if row[PERSON_ID] == person_id and row[ROLE] == role:
            return row_id
    return None


@needs_person_project_cache
def link(person_id, project_code, role):
    """
    Put an existing person on an existing project with this role;
    returns the link's id. The person is given the role in the People
    table if they didn't already have it.
    """
    people.check_role(role)
    _check_person(person_id)
    _check_project(project_code)
    if _find_link(person_id, project_code, role) is not None:
        raise ValueError(f'Person {person_id} is already a {role} on '
                         + f'project {project_code}')
    people.add_role(person_id, role)
    row_id = uuid4().hex
    get_cache(COLLECT).add({ID: row_id, PERSON_ID: person_id,
                            PROJECT_CODE: project_code, ROLE: role})
    return row_id


@needs_person_project_cache
def unlink(person_id, project_code, role):
    """
    Take this role on this project away from a person. Their other
    roles, and the person record itself, are kept.
    """
    people.check_role(role)
    row_id = _find_link(person_id, project_code, role)
    if row_id is None:
        raise ValueError(f'Person {person_id} is not a {role} on project '
                         + f'{project_code}')
    return get_cache(COLLECT).delete(row_id)


def fetch_people(project_code, role=None):
    """
    Get the people on a project, optionally only those with this role on
    it: returns a list sorted by name, each person listed once.
    """
    _check_project(project_code)
    if role is not None:
        people.check_role(role)
    person_ids = {row[PERSON_ID]
                  for row in _project_rows(project_code).values()
                  if role is None or row[ROLE] == role}
    found = [people.fetch_by_key(person_id) for person_id in person_ids]
    return sorted((person for person in found if person is not None),
                  key=lambda person: person[people.NAME].casefold())


def fetch_authors(project_code):
    """
    Get the authors on a project: returns a list sorted by name.
    """
    return fetch_people(project_code, people.AUTHOR)


def fetch_roles(person_id, project_code):
    """
    Get the roles this person has on this project.
    """
    _check_person(person_id)
    _check_project(project_code)
    return [row[ROLE] for row in _project_rows(project_code).values()
            if row[PERSON_ID] == person_id]


def fetch_projects(person_id, role=None):
    """
    Get the codes of the projects a person is on, optionally only those
    where they have this role.
    """
    _check_person(person_id)
    if role is not None:
        people.check_role(role)
    codes = [row[PROJECT_CODE] for row in _person_rows(person_id).values()
             if role is None or row[ROLE] == role]
    return list(dict.fromkeys(codes))


def roles_in_use(person_id):
    """
    Get the roles this person has on at least one project.
    """
    return {row[ROLE] for row in _person_rows(person_id).values()}


def _find_or_add_person(name):
    """
    Reuse the person with this name, or add a new person who is an
    author. (link gives a reused person the author role.)
    """
    existing = people.fetch_by_name(name)
    if existing:
        return next(iter(existing))
    return people.add(name, [people.AUTHOR])


def set_authors(project_code, names):
    """
    Make the project's authors exactly this list of names.
    Names already in the People table are reused; new ones are added.
    Only author links are changed: someone who is also a referee (or
    editor...) on the project keeps that role. Returns the project's
    authors as fetch_authors does.
    """
    _check_project(project_code)
    if not isinstance(names, list):
        raise ValueError('Authors must be a list of names.')
    # Check every name before changing anything.
    for name in names:
        people.check_name(name)
    wanted = {_find_or_add_person(name) for name in names}
    current = {person[people.ID] for person in fetch_authors(project_code)}
    for person_id in current - wanted:
        unlink(person_id, project_code, people.AUTHOR)
    for person_id in wanted - current:
        link(person_id, project_code, people.AUTHOR)
    return fetch_authors(project_code)


@needs_person_project_cache
def delete_project_links(project_code):
    """
    Remove every link to this project. Called when the project is deleted.
    """
    for row_id in list(_project_rows(project_code)):
        get_cache(COLLECT).delete(row_id)


@needs_person_project_cache
def delete_person_links(person_id):
    """
    Remove every link to this person. Called when the person is deleted.
    """
    for row_id in list(_person_rows(person_id)):
        get_cache(COLLECT).delete(row_id)
