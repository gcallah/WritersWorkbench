"""Contributor records can be linked to a person from the web screens."""
import pytest
from backendcore.data.caching import get_cache

from projects import contributors as contribs, query


def _remove(code):
    for record in contribs.fetch_list(code):
        get_cache(contribs.COLLECT).delete(record['id'])
    query.delete(code)


@pytest.fixture
def volume():
    code = query.add({**query.TEST_SAMPLE, query.TYPE: query.COLLECTION})
    yield code
    _remove(code)


def test_add_with_person_id(volume):
    record = contribs.add(volume, 'Ada', 'person1')
    assert record[contribs.PERSON_ID] == 'person1'
    get_cache(contribs.COLLECT).clear_cache()
    assert contribs.fetch_for_person(volume, 'person1')['id'] == record['id']


def test_add_without_person_id_is_unlinked(volume):
    record = contribs.add(volume, 'Ada')
    assert record[contribs.PERSON_ID] is None
    assert contribs.fetch_by_person(volume) == {}
    assert contribs.fetch_for_person(volume, 'person1') is None


def test_ensure_creates_the_record_once(volume):
    first = contribs.ensure_for_person(volume, 'p1', 'Ada')
    second = contribs.ensure_for_person(volume, 'p1', 'Ada')
    assert first['id'] == second['id']
    assert len(contribs.fetch_list(volume)) == 1


def test_same_name_different_people_get_different_records(volume):
    first = contribs.ensure_for_person(volume, 'p1', 'Ada')
    second = contribs.ensure_for_person(volume, 'p2', 'Ada')
    assert first['id'] != second['id']
    assert set(contribs.fetch_by_person(volume)) == {'p1', 'p2'}


def test_links_are_per_project(volume):
    other = query.add({**query.TEST_SAMPLE, query.TYPE: query.COLLECTION})
    try:
        mine = contribs.ensure_for_person(volume, 'p1', 'Ada')
        assert contribs.fetch_for_person(other, 'p1') is None
        theirs = contribs.ensure_for_person(other, 'p1', 'Ada')
        assert theirs['id'] != mine['id']
    finally:
        _remove(other)


@pytest.mark.parametrize('person_id', ['', 5, ['p1']])
def test_invalid_person_id(volume, person_id):
    with pytest.raises(ValueError):
        contribs.add(volume, 'Ada', person_id)
    assert contribs.fetch_list(volume) == []