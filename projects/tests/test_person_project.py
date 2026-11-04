"""The person_project join table links people to projects, with a role."""
from uuid import uuid4

import pytest
from backendcore.data.caching import get_cache

from projects import people, person_project as pp, query

AUTHOR = people.AUTHOR
REFEREE = people.REFEREE


def unique_name(prefix='Person'):
    """Names other tests (and old test data) won't collide with."""
    return f'{prefix} {uuid4().hex[:8]}'


@pytest.fixture
def project():
    code = query.add(query.TEST_SAMPLE)
    yield code
    if query.is_valid(code):
        query.delete(code)


@pytest.fixture
def other_project():
    code = query.add(query.TEST_SAMPLE)
    yield code
    if query.is_valid(code):
        query.delete(code)


@pytest.fixture
def person_id():
    person_id = people.add(unique_name(), [AUTHOR])
    yield person_id
    if people.is_valid(person_id):
        people.delete(person_id)


@pytest.fixture
def referee_id():
    referee_id = people.add(unique_name('Referee'), [REFEREE])
    yield referee_id
    if people.is_valid(referee_id):
        people.delete(referee_id)


def delete_people(names):
    for name in names:
        for person_id in people.fetch_by_name(name):
            people.delete(person_id)


def test_link_persists(project, person_id):
    pp.link(person_id, project, AUTHOR)
    get_cache(pp.COLLECT).clear_cache()
    assert pp.fetch_people(project) == [people.fetch_by_key(person_id)]
    assert pp.fetch_roles(person_id, project) == [AUTHOR]
    assert pp.fetch_projects(person_id) == [project]


def test_link_duplicate(project, person_id):
    pp.link(person_id, project, AUTHOR)
    with pytest.raises(ValueError):
        pp.link(person_id, project, AUTHOR)
    assert pp.fetch_roles(person_id, project) == [AUTHOR]


def test_link_bad_role(project, person_id):
    with pytest.raises(ValueError):
        pp.link(person_id, project, 'boss')
    assert pp.fetch_people(project) == []


def test_link_missing_person(project):
    with pytest.raises(ValueError):
        pp.link('missing', project, AUTHOR)
    assert pp.fetch_people(project) == []


def test_link_missing_project(person_id):
    with pytest.raises(ValueError):
        pp.link(person_id, 'missing', AUTHOR)
    assert pp.fetch_projects(person_id) == []


def test_link_gives_person_the_role(project, person_id):
    pp.link(person_id, project, REFEREE)
    assert people.fetch_by_key(person_id)[people.ROLES] == [AUTHOR, REFEREE]


def test_two_roles_on_one_project(project, person_id):
    pp.link(person_id, project, AUTHOR)
    pp.link(person_id, project, REFEREE)
    assert sorted(pp.fetch_roles(person_id, project)) == [AUTHOR, REFEREE]
    # Listed once, even with two roles.
    assert pp.fetch_people(project) == [people.fetch_by_key(person_id)]
    assert pp.fetch_projects(person_id) == [project]


def test_different_roles_on_different_projects(project, other_project,
                                               person_id):
    people.add_role(person_id, REFEREE)
    pp.link(person_id, project, AUTHOR)
    pp.link(person_id, other_project, REFEREE)
    # Being a referee somewhere else doesn't make them one here.
    assert pp.fetch_people(project, REFEREE) == []
    assert pp.fetch_authors(other_project) == []
    assert pp.fetch_projects(person_id, AUTHOR) == [project]
    assert pp.fetch_projects(person_id, REFEREE) == [other_project]
    assert set(pp.fetch_projects(person_id)) == {project, other_project}


def test_fetch_people_by_role(project, person_id, referee_id):
    pp.link(person_id, project, AUTHOR)
    pp.link(referee_id, project, REFEREE)
    assert len(pp.fetch_people(project)) == 2
    assert pp.fetch_people(project, REFEREE) == [
        people.fetch_by_key(referee_id)]
    assert pp.fetch_authors(project) == [people.fetch_by_key(person_id)]


def test_fetch_people_bad_role(project):
    with pytest.raises(ValueError):
        pp.fetch_people(project, 'boss')


def test_unlink_keeps_person_and_other_roles(project, person_id):
    pp.link(person_id, project, AUTHOR)
    pp.link(person_id, project, REFEREE)
    pp.unlink(person_id, project, AUTHOR)
    assert pp.fetch_roles(person_id, project) == [REFEREE]
    assert pp.fetch_authors(project) == []
    assert people.is_valid(person_id)


def test_unlink_not_linked(project, person_id):
    with pytest.raises(ValueError):
        pp.unlink(person_id, project, AUTHOR)
    pp.link(person_id, project, AUTHOR)
    with pytest.raises(ValueError):
        pp.unlink(person_id, project, REFEREE)


def test_fetch_missing(project):
    with pytest.raises(ValueError):
        pp.fetch_people('missing')
    with pytest.raises(ValueError):
        pp.fetch_projects('missing')
    with pytest.raises(ValueError):
        pp.fetch_roles('missing', project)


def test_cannot_drop_role_in_use(project, person_id):
    pp.link(person_id, project, REFEREE)
    with pytest.raises(ValueError):
        people.remove_role(person_id, REFEREE)
    assert people.has_role(people.fetch_by_key(person_id), REFEREE)
    # Once they're off the project, the role can go.
    pp.unlink(person_id, project, REFEREE)
    people.remove_role(person_id, REFEREE)
    assert people.fetch_by_key(person_id)[people.ROLES] == [AUTHOR]


def test_set_authors(project):
    names = [unique_name('Zed'), unique_name('Ada')]
    try:
        result = pp.set_authors(project, names)
        assert [person[people.NAME] for person in result] == sorted(names)
        assert all(person[people.ROLES] == [AUTHOR] for person in result)
        get_cache(pp.COLLECT).clear_cache()
        assert pp.fetch_authors(project) == result
    finally:
        delete_people(names)


def test_set_authors_replaces_list(project):
    keep, drop, new = unique_name(), unique_name(), unique_name()
    try:
        pp.set_authors(project, [keep, drop])
        result = pp.set_authors(project, [keep, new])
        assert {person[people.NAME] for person in result} == {keep, new}
        # Dropped authors leave the project but stay in the People table.
        assert people.fetch_by_name(drop)
    finally:
        delete_people([keep, drop, new])


def test_set_authors_reuses_existing_person(project, person_id):
    name = people.fetch_by_key(person_id)[people.NAME]
    result = pp.set_authors(project, [name, name])
    assert result == [people.fetch_by_key(person_id)]
    assert len(people.fetch_by_name(name)) == 1


def test_set_authors_gives_referee_author_role(project, referee_id):
    name = people.fetch_by_key(referee_id)[people.NAME]
    result = pp.set_authors(project, [name])
    assert [person[people.ID] for person in result] == [referee_id]
    assert people.fetch_by_key(referee_id)[people.ROLES] == [REFEREE, AUTHOR]


def test_set_authors_keeps_other_roles(project, person_id):
    # This person is both an author and a referee on the project.
    pp.link(person_id, project, AUTHOR)
    pp.link(person_id, project, REFEREE)
    pp.set_authors(project, [])
    assert pp.fetch_authors(project) == []
    assert pp.fetch_roles(person_id, project) == [REFEREE]


def test_set_authors_only_counts_this_project(project, other_project,
                                              person_id):
    pp.link(person_id, other_project, AUTHOR)
    assert pp.set_authors(project, []) == []
    assert pp.fetch_projects(person_id, AUTHOR) == [other_project]


def test_set_authors_empty_list(project, person_id):
    pp.link(person_id, project, AUTHOR)
    assert pp.set_authors(project, []) == []


@pytest.mark.parametrize('names', ['Ada', None, {'name': 'Ada'}])
def test_set_authors_not_a_list(project, names):
    with pytest.raises(ValueError):
        pp.set_authors(project, names)


def test_set_authors_bad_name_changes_nothing(project, person_id):
    pp.link(person_id, project, AUTHOR)
    good = unique_name()
    with pytest.raises(ValueError):
        pp.set_authors(project, [good, ''])
    assert pp.fetch_authors(project) == [people.fetch_by_key(person_id)]
    assert people.fetch_by_name(good) == {}


def test_set_authors_missing_project():
    with pytest.raises(ValueError):
        pp.set_authors('missing', [unique_name()])


def test_deleting_project_removes_links(project, person_id):
    pp.link(person_id, project, AUTHOR)
    query.delete(project)
    assert pp.fetch_projects(person_id) == []
    assert people.is_valid(person_id)


def test_deleting_person_removes_links(project, person_id):
    pp.link(person_id, project, AUTHOR)
    people.delete(person_id)
    assert pp.fetch_people(project) == []
