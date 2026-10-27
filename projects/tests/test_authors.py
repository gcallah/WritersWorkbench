"""Author records are persistent and validated."""
import pytest
from backendcore.data.caching import get_cache

from projects import authors


@pytest.fixture
def author_id():
    author_id = authors.add(authors.TEST_NAME)
    yield author_id
    if authors.is_valid(author_id):
        authors.delete(author_id)


def test_add_persists(author_id):
    get_cache(authors.COLLECT).clear_cache()
    assert authors.fetch_by_key(author_id) == {
        authors.ID: author_id, authors.NAME: authors.TEST_NAME}
    assert author_id in authors.fetch_dict()


def test_add_strips_name():
    author_id = authors.add('  Ada Lovelace  ')
    try:
        assert authors.fetch_by_key(author_id)[authors.NAME] == 'Ada Lovelace'
    finally:
        authors.delete(author_id)


def test_same_names_have_distinct_ids(author_id):
    other = authors.add(authors.TEST_NAME)
    try:
        assert other != author_id
        assert {author_id, other} <= set(
            authors.fetch_by_name(authors.TEST_NAME))
    finally:
        authors.delete(other)


@pytest.mark.parametrize('name', [None, '', '  ', 3, 'a' * 201])
def test_add_invalid_name(name):
    count = len(authors.fetch_dict())
    with pytest.raises(ValueError):
        authors.add(name)
    assert len(authors.fetch_dict()) == count


def test_fetch_missing():
    assert authors.fetch_by_key('missing') is None
    assert not authors.is_valid('missing')


def test_fetch_by_name_unknown():
    assert authors.fetch_by_name('Nobody By This Name') == {}


def test_update(author_id):
    authors.update(author_id, 'New Name')
    get_cache(authors.COLLECT).clear_cache()
    assert authors.fetch_by_key(author_id)[authors.NAME] == 'New Name'


def test_update_invalid_name(author_id):
    with pytest.raises(ValueError):
        authors.update(author_id, '')
    assert authors.fetch_by_key(author_id)[authors.NAME] == authors.TEST_NAME


def test_update_missing():
    with pytest.raises(ValueError):
        authors.update('missing', 'New Name')


def test_delete(author_id):
    authors.delete(author_id)
    assert not authors.is_valid(author_id)


def test_delete_missing():
    with pytest.raises(ValueError):
        authors.delete('missing')
