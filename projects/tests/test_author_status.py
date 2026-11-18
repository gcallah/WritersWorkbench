"""Author rows in person_project record received pieces and referees."""
import pytest
from backendcore.data.caching import get_cache

from projects import people, query
import projects.person_project as pp


@pytest.fixture
def project():
    code = query.add({**query.TEST_SAMPLE, query.TYPE: query.COLLECTION})
    yield code
    query.delete(code)


@pytest.fixture
def author(project):
    person_id = people.add(people.TEST_NAME, [people.AUTHOR])
    pp.link(person_id, project, people.AUTHOR)
    yield person_id
    if people.is_valid(person_id):
        people.delete(person_id)


def _reload():
    """Drop the cache so the next read comes from the database."""
    get_cache(pp.COLLECT).clear_cache()


def test_new_author_has_nothing_received(project, author):
    status = pp.fetch_author_status(project, author)
    assert status == {**{flag: False for flag in pp.RECEIVED_FLAGS},
                      pp.HAS_REFEREE: None}


def test_status_survives_reload(project, author):
    _reload()
    status = pp.fetch_author_status(project, author)
    assert all(status[flag] is False for flag in pp.RECEIVED_FLAGS)
    assert status[pp.HAS_REFEREE] is None


@pytest.mark.parametrize('piece', list(pp.PIECES))
def test_mark_received_sets_only_that_flag(project, author, piece):
    flag = pp.PIECES[piece][1]
    status = pp.mark_received(project, author, piece)
    assert status[flag] is True
    _reload()
    status = pp.fetch_author_status(project, author)
    assert status[flag] is True
    assert not any(status[other] for other in pp.RECEIVED_FLAGS
                   if other != flag)


def test_mark_received_rejects_unknown_piece(project, author):
    with pytest.raises(ValueError):
        pp.mark_received(project, author, 'poem')
    assert not any(pp.fetch_author_status(project, author)[flag]
                   for flag in pp.RECEIVED_FLAGS)


@pytest.mark.parametrize('answer', [True, False])
def test_set_referee_persists(project, author, answer):
    assert pp.set_referee(project, author, answer)[pp.HAS_REFEREE] is answer
    _reload()
    assert pp.fetch_author_status(project, author)[pp.HAS_REFEREE] is answer


@pytest.mark.parametrize('answer', [None, 'yes', 1, 0])
def test_set_referee_rejects_non_boolean(project, author, answer):
    with pytest.raises(ValueError):
        pp.set_referee(project, author, answer)
    assert pp.fetch_author_status(project, author)[pp.HAS_REFEREE] is None


def test_status_is_per_project(project, author):
    other = query.add({**query.TEST_SAMPLE, query.TYPE: query.COLLECTION})
    try:
        pp.link(author, other, people.AUTHOR)
        pp.mark_received(project, author, 'bio')
        assert pp.fetch_author_status(other, author)['Bio'] is False
    finally:
        query.delete(other)


def test_non_author_has_no_status(project):
    referee = people.add('A Referee', [people.REFEREE])
    try:
        pp.link(referee, project, people.REFEREE)
        with pytest.raises(KeyError):
            pp.fetch_author_status(project, referee)
        with pytest.raises(KeyError):
            pp.mark_received(project, referee, 'bio')
        with pytest.raises(KeyError):
            pp.set_referee(project, referee, True)
    finally:
        people.delete(referee)


def test_other_roles_get_no_piece_fields(project):
    editor = people.add('An Editor', [people.EDITOR])
    try:
        row_id = pp.link(editor, project, people.EDITOR)
        row = get_cache(pp.COLLECT).fetch_by_key(row_id)
        # SQLite gives every row every column, so check for no value.
        assert all(row.get(flag) is None for flag in pp.RECEIVED_FLAGS)
    finally:
        people.delete(editor)


def test_relinking_author_starts_fresh(project, author):
    pp.mark_received(project, author, 'bio')
    pp.unlink(author, project, people.AUTHOR)
    pp.link(author, project, people.AUTHOR)
    assert pp.fetch_author_status(project, author)['Bio'] is False


def test_contributors_shares_pieces():
    from projects import contributors
    assert contributors.PIECES is pp.PIECES
