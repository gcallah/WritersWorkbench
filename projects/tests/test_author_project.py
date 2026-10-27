"""The author_project join table links authors and projects."""
from uuid import uuid4

import pytest
from backendcore.data.caching import get_cache

from projects import author_project as ap, authors, query


def unique_name(prefix='Author'):
    """Names other tests (and old test data) won't collide with."""
    return f'{prefix} {uuid4().hex[:8]}'


@pytest.fixture
def project():
    code = query.add(query.TEST_SAMPLE)
    yield code
    if query.is_valid(code):
        query.delete(code)


@pytest.fixture
def author_id():
    author_id = authors.add(unique_name())
    yield author_id
    if authors.is_valid(author_id):
        authors.delete(author_id)


def delete_authors(names):
    for name in names:
        for author_id in authors.fetch_by_name(name):
            authors.delete(author_id)


def test_link_persists(project, author_id):
    ap.link(author_id, project)
    get_cache(ap.COLLECT).clear_cache()
    assert ap.fetch_authors(project) == [authors.fetch_by_key(author_id)]
    assert ap.fetch_projects(author_id) == [project]


def test_link_duplicate(project, author_id):
    ap.link(author_id, project)
    with pytest.raises(ValueError):
        ap.link(author_id, project)
    assert len(ap.fetch_authors(project)) == 1


def test_link_missing_author(project):
    with pytest.raises(ValueError):
        ap.link('missing', project)
    assert ap.fetch_authors(project) == []


def test_link_missing_project(author_id):
    with pytest.raises(ValueError):
        ap.link(author_id, 'missing')
    assert ap.fetch_projects(author_id) == []


def test_author_on_many_projects(project, author_id):
    other = query.add(query.TEST_SAMPLE)
    try:
        ap.link(author_id, project)
        ap.link(author_id, other)
        assert set(ap.fetch_projects(author_id)) == {project, other}
    finally:
        query.delete(other)


def test_unlink_keeps_author(project, author_id):
    ap.link(author_id, project)
    ap.unlink(author_id, project)
    assert ap.fetch_authors(project) == []
    assert authors.is_valid(author_id)


def test_unlink_not_linked(project, author_id):
    with pytest.raises(ValueError):
        ap.unlink(author_id, project)


def test_fetch_missing():
    with pytest.raises(ValueError):
        ap.fetch_authors('missing')
    with pytest.raises(ValueError):
        ap.fetch_projects('missing')


def test_set_authors(project):
    names = [unique_name('Zed'), unique_name('Ada')]
    try:
        result = ap.set_authors(project, names)
        assert [author[authors.NAME] for author in result] == sorted(names)
        get_cache(ap.COLLECT).clear_cache()
        assert ap.fetch_authors(project) == result
    finally:
        delete_authors(names)


def test_set_authors_replaces_list(project):
    keep, drop, new = unique_name(), unique_name(), unique_name()
    try:
        ap.set_authors(project, [keep, drop])
        result = ap.set_authors(project, [keep, new])
        assert {author[authors.NAME] for author in result} == {keep, new}
        # Dropped authors leave the project but stay in the author table.
        assert authors.fetch_by_name(drop)
    finally:
        delete_authors([keep, drop, new])


def test_set_authors_reuses_existing_author(project, author_id):
    name = authors.fetch_by_key(author_id)[authors.NAME]
    result = ap.set_authors(project, [name, name])
    assert result == [authors.fetch_by_key(author_id)]
    assert len(authors.fetch_by_name(name)) == 1


def test_set_authors_empty_list(project, author_id):
    ap.link(author_id, project)
    assert ap.set_authors(project, []) == []


@pytest.mark.parametrize('names', ['Ada', None, {'name': 'Ada'}])
def test_set_authors_not_a_list(project, names):
    with pytest.raises(ValueError):
        ap.set_authors(project, names)


def test_set_authors_bad_name_changes_nothing(project, author_id):
    ap.link(author_id, project)
    good = unique_name()
    with pytest.raises(ValueError):
        ap.set_authors(project, [good, ''])
    assert ap.fetch_authors(project) == [authors.fetch_by_key(author_id)]
    assert authors.fetch_by_name(good) == {}


def test_set_authors_missing_project():
    with pytest.raises(ValueError):
        ap.set_authors('missing', [unique_name()])


def test_deleting_project_removes_links(project, author_id):
    ap.link(author_id, project)
    query.delete(project)
    assert ap.fetch_projects(author_id) == []
    assert authors.is_valid(author_id)


def test_deleting_author_removes_links(project, author_id):
    ap.link(author_id, project)
    authors.delete(author_id)
    assert ap.fetch_authors(project) == []
