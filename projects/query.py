"""
This is our interface to projects data.
Every project must have a name, a user, and a type.
"""
from uuid import uuid4

from backendcore.data.caching import needs_cache, get_cache
import backendcore.data.fields as cflds

from projects.storage import prepare_project

DB = 'projectsDB'
COLLECT = 'Projects'

# Field names:
CODE = cflds.CODE
NAME = cflds.NAME
USER = 'user'
TYPE = 'type'

REQUIRED_FLDS = [NAME, USER, TYPE]

# Project requirements, distinct from each contributor's received flags.
REQUIRES_BIO = 'requires_bio'
REQUIRES_PERMISSION = 'requires_permission'
REQUIRES_ADDRESS = 'requires_address'
REQUIREMENT_FIELDS = (REQUIRES_BIO, REQUIRES_PERMISSION, REQUIRES_ADDRESS)


def _check_requirements(project):
    for field in REQUIREMENT_FIELDS:
        if field in project and type(project[field]) is not bool:
            raise ValueError(f'Project {field} must be true or false.')


def _with_requirements(project):
    if project is None:
        return None
    result = dict(project)
    for field in REQUIREMENT_FIELDS:
        # Older SQLite rows may have NULL after a new column is added.
        if result.get(field) is None:
            result[field] = False
    return result


# Project types: to add a type, just add an entry here.
SOLO_BOOK = 'solo_book'
COLLECTION = 'collection'
ESSAY = 'essay'

PROJECT_TYPES = {
    SOLO_BOOK: {cflds.DESCR: 'Solo Book'},
    COLLECTION: {cflds.DESCR: 'Edited volume (multi-author)'},
    ESSAY: {cflds.DESCR: 'Essay'},
}

FIELDS = {
    NAME: {
        cflds.DISP_NAME: 'Project Name',
    },
    USER: {
        cflds.DISP_NAME: 'User',
    },
    TYPE: {
        cflds.DISP_NAME: 'Project Type',
        cflds.CHOICES: PROJECT_TYPES,
    },
}


def needs_projects_cache(fn):
    """
    Should be used to decorate any function that uses datacollection methods.
    """
    return needs_cache(fn, COLLECT, DB, COLLECT, key_fld=CODE)


def get_type_choices() -> dict:
    """
    The pick list for project types: {type: description}.
    """
    return cflds.get_choices(FIELDS, TYPE)


def is_valid_type(proj_type) -> bool:
    return cflds.is_valid_choice(FIELDS, TYPE, proj_type)


def _check_fld(fld_nm, val):
    if not isinstance(val, str) or not val.strip():
        raise ValueError(f'Project {fld_nm} must be a non-empty string.')
    if fld_nm == TYPE and not is_valid_type(val):
        raise ValueError(f'Invalid project {TYPE}: {val}; must be one of '
                         + f'{list(PROJECT_TYPES.keys())}')


def is_valid(code):
    return code in fetch_dict()


@needs_projects_cache
def fetch_list():
    """
    Fetch all projects: returns a list
    """
    return [_with_requirements(p) for p in get_cache(COLLECT).fetch_list()]


@needs_projects_cache
def fetch_dict():
    """
    Fetch all projects: returns a dict keyed by project code.
    """
    return {code: _with_requirements(p)
            for code, p in get_cache(COLLECT).fetch_dict().items()}


@needs_projects_cache
def get_choices():
    return get_cache(COLLECT).get_choices()


def fetch_codes():
    """
    Fetch all project codes
    """
    return list(fetch_dict().keys())


@needs_projects_cache
def fetch_by_key(code):
    """
    Get a single project by its code.
    """
    return _with_requirements(get_cache(COLLECT).fetch_by_key(code))


@needs_projects_cache
def fetch_by_user(user):
    """
    Get all projects belonging to a user: returns a dict keyed by code.
    """
    return {code: _with_requirements(p) for code, p in
            get_cache(COLLECT).fetch_by_fld_val(USER, user).items()}


@needs_projects_cache
def add(project: dict):
    """
    Create a project. Name, user, and type are required.
    A unique code is generated for the project and returned.
    """
    for fld_nm in REQUIRED_FLDS:
        _check_fld(fld_nm, project.get(fld_nm))
    _check_requirements(project)
    project = _with_requirements(project)
    project[CODE] = uuid4().hex
    prepare_project(project[CODE], project[TYPE] == COLLECTION)
    get_cache(COLLECT).add(project)
    return project[CODE]


@needs_projects_cache
def update(code, update_dict: dict):
    """
    Update the fields in update_dict for the project with this code.
    The code itself can't be changed.
    """
    if CODE in update_dict:
        raise ValueError(f'Project {CODE} can not be updated.')
    for fld_nm in REQUIRED_FLDS:
        if fld_nm in update_dict:
            _check_fld(fld_nm, update_dict[fld_nm])
    _check_requirements(update_dict)
    existing = fetch_by_key(code)
    if existing is None:
        raise ValueError(f'No project with code {code}')
    prepare_project(code, update_dict.get(TYPE, existing[TYPE]) == COLLECTION)
    return get_cache(COLLECT).update(code, update_dict)


@needs_projects_cache
def delete(code):
    # Imported here: author_project imports this module.
    from projects import author_project
    author_project.delete_project_links(code)
    return get_cache(COLLECT).delete(code)


TEST_USER = 'test_user@example.com'

TEST_SAMPLE = {
    NAME: 'A Test Project',
    USER: TEST_USER,
    TYPE: SOLO_BOOK,
}


def main():
    """
    Run this as a program to see the output formats!
    """
    print("Interactive test of projects data module.")
    print(f'{get_type_choices()=}')
    print(f'{fetch_list()=}')


if __name__ == '__main__':
    main()
