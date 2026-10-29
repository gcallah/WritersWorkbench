"""Project contributors and receipt flags, stored through BackEndCore."""
from uuid import uuid4

from backendcore.data.caching import get_cache, needs_cache

from projects import query


COLLECT = 'ProjectContributors'
ID = 'id'
PROJECT = 'project_code'
NAME = 'name'
HAS_REFEREE = 'HasReferee'
# Preserve the editor's existing Bio and Submission names.
PIECES = {
    'bio': ('bios', 'Bio'),
    'submission': ('chapters', 'Submission'),
    'abstract': ('abstracts', 'Abstract'),
    'address': ('addresses', 'Address'),
    'keywords': ('keywords', 'Keywords'),
    'permission': ('permissions', 'Permission'),
    'referee_report': ('referee_reports', 'RefereeReport'),
}


def needs_contributors(fn):
    return needs_cache(fn, COLLECT, query.DB, COLLECT, key_fld=ID)


def require_volume(project_code):
    project = query.fetch_by_key(project_code)
    if project is None:
        raise KeyError('Project not found.')
    if project[query.TYPE] != query.COLLECTION:
        raise ValueError('Contributors require an edited-volume project.')
    return project


@needs_contributors
def add(project_code, name):
    """Register a contributor in one edited volume; return their record."""
    require_volume(project_code)
    if not isinstance(name, str) or not name.strip() or len(name) > 200:
        raise ValueError('Enter a contributor name of 1 to 200 characters.')
    record = {ID: uuid4().hex, PROJECT: project_code, NAME: name.strip()}
    record.update({flag: False for _, flag in PIECES.values()})
    record[HAS_REFEREE] = None
    get_cache(COLLECT).add(dict(record))
    return record


def _with_referee(record):
    result = dict(record)
    result.setdefault(HAS_REFEREE, None)
    return result


@needs_contributors
def fetch_list(project_code):
    """Return only contributors belonging to this edited volume."""
    require_volume(project_code)
    records = get_cache(COLLECT).fetch_by_fld_val(PROJECT, project_code)
    return sorted((_with_referee(record) for record in records.values()),
                  key=lambda record: record[NAME].casefold())


@needs_contributors
def fetch(project_code, contributor_id):
    require_volume(project_code)
    record = get_cache(COLLECT).fetch_by_key(contributor_id)
    if record is None or record[PROJECT] != project_code:
        raise KeyError('Contributor not found in this project.')
    return _with_referee(record)


@needs_contributors
def set_referee(project_code, contributor_id, has_referee):
    """Save whether a paper has a referee, scoped to its project."""
    if type(has_referee) is not bool:
        raise ValueError('Referee answer must be true or false.')
    fetch(project_code, contributor_id)
    if not get_cache(COLLECT).update(
            contributor_id, {HAS_REFEREE: has_referee}):
        raise OSError('Could not update referee answer.')
    return fetch(project_code, contributor_id)


@needs_contributors
def mark_received(project_code, contributor_id, piece_type):
    """Called by storage only after the corresponding file is saved."""
    fetch(project_code, contributor_id)
    if piece_type not in PIECES:
        raise ValueError('Unknown piece type.')
    flag = PIECES[piece_type][1]
    if not get_cache(COLLECT).update(contributor_id, {flag: True}):
        raise OSError('Could not update receipt status.')
    return fetch(project_code, contributor_id)
