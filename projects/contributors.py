"""Project contributors and receipt flags, stored through BackEndCore."""
from uuid import uuid4

from backendcore.data.caching import get_cache, needs_cache

from projects import query
from projects.person_project import PIECES


COLLECT = 'ProjectContributors'
ID = 'id'
PROJECT = 'project_code'
NAME = 'name'
HAS_REFEREE = 'HasReferee'
# Set when the record was made from a person on the /web/ screens.
PERSON_ID = 'person_id'
# PIECES (imported above) now lives in person_project, where author rows
# keep the same received flags. contributors.PIECES still works until
# this module is removed (issue #34).


def needs_contributors(fn):
    return needs_cache(fn, COLLECT, query.DB, COLLECT, key_fld=ID)


def _validate_contributor_name(name):
    if not isinstance(name, str) or not name.strip() or len(name) > 200:
        raise ValueError('Enter a contributor name of 1 to 200 characters.')
    return name.strip()


def _validate_person_id(person_id):
    if person_id is not None and (not isinstance(person_id, str) or not person_id):
        raise ValueError('A person id must be a non-empty string.')
    return person_id


def _initialize_record(project_code, name, person_id):
    record = {ID: uuid4().hex, PROJECT: project_code, NAME: name}
    record.update({flag: False for _, flag in PIECES.values()})
    record[HAS_REFEREE] = None
    record[PERSON_ID] = person_id
    return record


def _with_defaults(record):
    result = dict(record)
    result.setdefault(HAS_REFEREE, None)
    result.setdefault(PERSON_ID, None)
    return result


def require_volume(project_code):
    project = query.fetch_by_key(project_code)
    if project is None:
        raise KeyError('Project not found.')
    if not query.is_multi_author(project[query.TYPE]):
        raise ValueError('Contributors need a multi-author project.')
    return project


@needs_contributors
def add(project_code, name, person_id=None):
    """Register a contributor in one edited volume; return their record.

    person_id links the record to a person from the People table."""
    require_volume(project_code)
    name = _validate_contributor_name(name)
    person_id = _validate_person_id(person_id)
    record = _initialize_record(project_code, name, person_id)
    get_cache(COLLECT).add(dict(record))
    return record


@needs_contributors
def fetch_list(project_code):
    """Return only contributors belonging to this edited volume."""
    require_volume(project_code)
    records = get_cache(COLLECT).fetch_by_fld_val(PROJECT, project_code)
    return sorted((_with_defaults(record) for record in records.values()),
                  key=lambda record: record[NAME].casefold())


@needs_contributors
def fetch(project_code, contributor_id):
    require_volume(project_code)
    record = get_cache(COLLECT).fetch_by_key(contributor_id)
    if record is None or record[PROJECT] != project_code:
        raise KeyError('Contributor not found in this project.')
    return _with_defaults(record)


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


def fetch_by_person(project_code):
    """Map person id to contributor record, for people linked in this book."""
    return {record[PERSON_ID]: record for record in fetch_list(project_code)
            if record.get(PERSON_ID)}


def fetch_for_person(project_code, person_id):
    """Return the contributor record linked to this person, or None."""
    return fetch_by_person(project_code).get(person_id)


def ensure_for_person(project_code, person_id, name):
    """Return this person's contributor record, creating it the first time."""
    record = fetch_for_person(project_code, person_id)
    if record is None:
        record = add(project_code, name, person_id)
    return record


@needs_contributors
def get_completion_status(project_code, contributor_id):
    """Return piece completion stats for a contributor.

    Returns:
        dict: {
            'contributor_id': str,
            'name': str,
            'received': int (count of received pieces),
            'total': int (total expected pieces),
            'percent': int (0-100),
            'display': str (e.g., "2/4 pieces received (50%)")
        }
    """
    record = fetch(project_code, contributor_id)
    piece_flags = {flag: record.get(flag, False) for _, flag in PIECES.values()}
    received = sum(1 for received_flag in piece_flags.values() if received_flag)
    total = len(piece_flags)
    percent = (received * 100) // total if total > 0 else 0

    return {
        'contributor_id': contributor_id,
        'name': record[NAME],
        'received': received,
        'total': total,
        'percent': percent,
        'display': f"{received}/{total} pieces received ({percent}%)"
    }


@needs_contributors
def fetch_all_completion_status(project_code):
    """Return completion stats for all contributors in a project.

    Returns:
        list: Sorted by name, each with completion status dict.
    """
    contributors = fetch_list(project_code)
    return sorted(
        (get_completion_status(project_code, c[ID]) for c in contributors),
        key=lambda s: s['name'].casefold()
    )
