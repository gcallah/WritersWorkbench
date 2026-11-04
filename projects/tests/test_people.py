"""People records are persistent and validated, and can have many roles."""
import pytest
from backendcore.data.caching import get_cache

from projects import people


@pytest.fixture
def person_id():
    person_id = people.add(people.TEST_NAME, people.TEST_ROLES)
    yield person_id
    if people.is_valid(person_id):
        people.delete(person_id)


def test_add_persists(person_id):
    get_cache(people.COLLECT).clear_cache()
    assert people.fetch_by_key(person_id) == {
        people.ID: person_id, people.NAME: people.TEST_NAME,
        people.ROLES: people.TEST_ROLES}
    assert person_id in people.fetch_dict()


def test_add_strips_name():
    person_id = people.add('  Ada Lovelace  ', [people.AUTHOR])
    try:
        assert people.fetch_by_key(person_id)[people.NAME] == 'Ada Lovelace'
    finally:
        people.delete(person_id)


def test_add_many_roles():
    roles = [people.AUTHOR, people.REFEREE, people.AUTHOR]
    person_id = people.add(people.TEST_NAME, roles)
    try:
        get_cache(people.COLLECT).clear_cache()
        # Repeats are dropped; order is kept.
        assert people.fetch_by_key(person_id)[people.ROLES] == [
            people.AUTHOR, people.REFEREE]
    finally:
        people.delete(person_id)


def test_same_names_have_distinct_ids(person_id):
    other = people.add(people.TEST_NAME, [people.REFEREE])
    try:
        assert other != person_id
        assert {person_id, other} <= set(
            people.fetch_by_name(people.TEST_NAME))
    finally:
        people.delete(other)


@pytest.mark.parametrize('name', [None, '', '  ', 3, 'a' * 201])
def test_add_invalid_name(name):
    count = len(people.fetch_dict())
    with pytest.raises(ValueError):
        people.add(name, [people.AUTHOR])
    assert len(people.fetch_dict()) == count


@pytest.mark.parametrize('roles', [None, [], 'author', ['author', 'boss']])
def test_add_invalid_roles(roles):
    count = len(people.fetch_dict())
    with pytest.raises(ValueError):
        people.add(people.TEST_NAME, roles)
    assert len(people.fetch_dict()) == count


def test_fetch_missing():
    assert people.fetch_by_key('missing') is None
    assert not people.is_valid('missing')


def test_fetch_by_name_unknown():
    assert people.fetch_by_name('Nobody By This Name') == {}


def test_fetch_by_role(person_id):
    referee = people.add(people.TEST_NAME, [people.REFEREE, people.EDITOR])
    try:
        assert person_id in people.fetch_by_role(people.AUTHOR)
        assert referee not in people.fetch_by_role(people.AUTHOR)
        assert referee in people.fetch_by_role(people.REFEREE)
        assert referee in people.fetch_by_role(people.EDITOR)
    finally:
        people.delete(referee)


def test_fetch_by_bad_role():
    with pytest.raises(ValueError):
        people.fetch_by_role('boss')


def test_update(person_id):
    people.update(person_id, 'New Name')
    get_cache(people.COLLECT).clear_cache()
    assert people.fetch_by_key(person_id)[people.NAME] == 'New Name'


def test_update_invalid_name(person_id):
    with pytest.raises(ValueError):
        people.update(person_id, '')
    assert people.fetch_by_key(person_id)[people.NAME] == people.TEST_NAME


def test_update_missing():
    with pytest.raises(ValueError):
        people.update('missing', 'New Name')


def test_set_roles(person_id):
    people.set_roles(person_id, [people.COPY_EDITOR, people.REFEREE])
    get_cache(people.COLLECT).clear_cache()
    assert people.fetch_by_key(person_id)[people.ROLES] == [
        people.COPY_EDITOR, people.REFEREE]


def test_set_roles_invalid(person_id):
    with pytest.raises(ValueError):
        people.set_roles(person_id, [])
    with pytest.raises(ValueError):
        people.set_roles('missing', [people.AUTHOR])
    assert people.fetch_by_key(person_id)[people.ROLES] == people.TEST_ROLES


def test_add_role(person_id):
    people.add_role(person_id, people.REFEREE)
    # Adding a role they already have changes nothing.
    people.add_role(person_id, people.REFEREE)
    assert people.fetch_by_key(person_id)[people.ROLES] == [
        people.AUTHOR, people.REFEREE]


def test_add_bad_role(person_id):
    with pytest.raises(ValueError):
        people.add_role(person_id, 'boss')


def test_remove_role(person_id):
    people.add_role(person_id, people.EDITOR)
    people.remove_role(person_id, people.AUTHOR)
    assert people.fetch_by_key(person_id)[people.ROLES] == [people.EDITOR]


def test_remove_last_role(person_id):
    with pytest.raises(ValueError):
        people.remove_role(person_id, people.AUTHOR)
    assert people.fetch_by_key(person_id)[people.ROLES] == people.TEST_ROLES


def test_remove_role_not_held(person_id):
    with pytest.raises(ValueError):
        people.remove_role(person_id, people.REFEREE)


def test_delete(person_id):
    people.delete(person_id)
    assert not people.is_valid(person_id)


def test_delete_missing():
    with pytest.raises(ValueError):
        people.delete('missing')
