"""Contributor records are persistent and scoped to their project."""
import pytest
from backendcore.data.caching import get_cache

from projects import contributors as people, query


@pytest.fixture
def volume():
    code = query.add({**query.TEST_SAMPLE, query.TYPE: query.COLLECTION})
    yield code
    for person in people.fetch_list(code):
        get_cache(people.COLLECT).delete(person['id'])
    query.delete(code)


def test_records_persist_and_same_names_have_distinct_ids(volume):
    first = people.add(volume, 'Ada')
    second = people.add(volume, 'Ada')
    assert first['id'] != second['id']
    assert all(first[flag] is False for _, flag in people.PIECES.values())
    get_cache(people.COLLECT).clear_cache()
    assert people.fetch(volume, first['id']) == first
    assert len(people.fetch_list(volume)) == 2


def test_cannot_access_contributor_through_other_project(volume):
    person = people.add(volume, 'Ada')
    other = query.add({**query.TEST_SAMPLE, query.TYPE: query.COLLECTION})
    try:
        assert people.fetch_list(other) == []
        with pytest.raises(KeyError):
            people.fetch(other, person['id'])
        with pytest.raises(KeyError):
            people.mark_received(other, person['id'], 'bio')
        assert not people.fetch(volume, person['id'])['Bio']
    finally:
        query.delete(other)


@pytest.mark.parametrize('name', [None, '', '  ', 3, 'a' * 201])
def test_invalid_name(volume, name):
    with pytest.raises(ValueError):
        people.add(volume, name)
    assert people.fetch_list(volume) == []


def test_missing_or_wrong_project_type():
    with pytest.raises(KeyError):
        people.add('missing', 'Ada')
    code = query.add(query.TEST_SAMPLE)
    try:
        with pytest.raises(ValueError):
            people.add(code, 'Ada')
    finally:
        query.delete(code)


def test_receipt_changes_only_selected_item(volume):
    person = people.add(volume, 'Ada')
    people.mark_received(volume, person['id'], 'bio')
    get_cache(people.COLLECT).clear_cache()
    record = people.fetch(volume, person['id'])
    assert record['Bio'] is True
    assert record['Submission'] is False
    with pytest.raises(ValueError):
        people.mark_received(volume, person['id'], 'unknown')


def test_referee_answer_persists_and_is_project_scoped(volume):
    person = people.add(volume, 'Ada')
    assert person[people.HAS_REFEREE] is None
    assert people.set_referee(volume, person['id'], True)[
        people.HAS_REFEREE] is True
    get_cache(people.COLLECT).clear_cache()
    assert people.fetch(volume, person['id'])[people.HAS_REFEREE] is True

    other = query.add({**query.TEST_SAMPLE, query.TYPE: query.COLLECTION})
    try:
        with pytest.raises(KeyError):
            people.set_referee(other, person['id'], False)
        assert people.fetch(volume, person['id'])[people.HAS_REFEREE] is True
    finally:
        query.delete(other)


@pytest.mark.parametrize('answer', [None, 0, 1, 'yes'])
def test_referee_answer_must_be_boolean(volume, answer):
    person = people.add(volume, 'Ada')
    with pytest.raises(ValueError, match='Referee answer'):
        people.set_referee(volume, person['id'], answer)
