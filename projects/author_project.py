"""
The author_project join table: links authors to projects.
An author can be on many projects, and a project can have many authors.
"""
from uuid import uuid4

from backendcore.data.caching import get_cache, needs_cache

from projects import authors, query

COLLECT = 'AuthorProject'

# Field names:
ID = 'id'
AUTHOR_ID = 'author_id'
PROJECT_CODE = 'project_code'


def needs_author_project_cache(fn):
    """
    Should be used to decorate any function that uses datacollection methods.
    """
    return needs_cache(fn, COLLECT, query.DB, COLLECT, key_fld=ID)


def _check_project(project_code):
    if query.fetch_by_key(project_code) is None:
        raise ValueError(f'No project with code {project_code}')


def _check_author(author_id):
    if not authors.is_valid(author_id):
        raise ValueError(f'No author with id {author_id}')


@needs_author_project_cache
def _project_rows(project_code):
    return get_cache(COLLECT).fetch_by_fld_val(PROJECT_CODE, project_code)


@needs_author_project_cache
def _author_rows(author_id):
    return get_cache(COLLECT).fetch_by_fld_val(AUTHOR_ID, author_id)


def _find_link(author_id, project_code):
    """
    Returns the id of the row linking this author and project, or None.
    """
    for row_id, row in _project_rows(project_code).items():
        if row[AUTHOR_ID] == author_id:
            return row_id
    return None


@needs_author_project_cache
def link(author_id, project_code):
    """
    Put an existing author on an existing project; returns the link's id.
    """
    _check_author(author_id)
    _check_project(project_code)
    if _find_link(author_id, project_code) is not None:
        raise ValueError(f'Author {author_id} is already on project '
                         + f'{project_code}')
    row_id = uuid4().hex
    get_cache(COLLECT).add({ID: row_id, AUTHOR_ID: author_id,
                            PROJECT_CODE: project_code})
    return row_id


@needs_author_project_cache
def unlink(author_id, project_code):
    """
    Take an author off a project. The author record itself is kept.
    """
    row_id = _find_link(author_id, project_code)
    if row_id is None:
        raise ValueError(f'Author {author_id} is not on project '
                         + f'{project_code}')
    return get_cache(COLLECT).delete(row_id)


def fetch_authors(project_code):
    """
    Get the authors on a project: returns a list sorted by name.
    """
    _check_project(project_code)
    found = [authors.fetch_by_key(row[AUTHOR_ID])
             for row in _project_rows(project_code).values()]
    return sorted((author for author in found if author is not None),
                  key=lambda author: author[authors.NAME].casefold())


def fetch_projects(author_id):
    """
    Get the codes of the projects an author is on.
    """
    _check_author(author_id)
    return [row[PROJECT_CODE] for row in _author_rows(author_id).values()]


def _find_or_add_author(name):
    existing = authors.fetch_by_name(name)
    if existing:
        return next(iter(existing))
    return authors.add(name)


def set_authors(project_code, names):
    """
    Make the project's authors exactly this list of names.
    Names already in the author table are reused; new ones are added.
    Returns the project's authors as fetch_authors does.
    """
    _check_project(project_code)
    if not isinstance(names, list):
        raise ValueError('Authors must be a list of names.')
    # Check every name before changing anything.
    for name in names:
        authors.check_name(name)
    wanted = {_find_or_add_author(name) for name in names}
    current = {row[AUTHOR_ID] for row in _project_rows(project_code).values()}
    for author_id in current - wanted:
        unlink(author_id, project_code)
    for author_id in wanted - current:
        link(author_id, project_code)
    return fetch_authors(project_code)


@needs_author_project_cache
def delete_project_links(project_code):
    """
    Remove every link to this project. Called when the project is deleted.
    """
    for row_id in list(_project_rows(project_code)):
        get_cache(COLLECT).delete(row_id)


@needs_author_project_cache
def delete_author_links(author_id):
    """
    Remove every link to this author. Called when the author is deleted.
    """
    for row_id in list(_author_rows(author_id)):
        get_cache(COLLECT).delete(row_id)
