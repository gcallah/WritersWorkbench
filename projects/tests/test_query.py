from copy import deepcopy

import pytest

import projects.query as qry


def get_sample():
    return deepcopy(qry.TEST_SAMPLE)


@pytest.fixture(scope='function')
def temp_project():
    code = qry.add(get_sample())
    yield code
    if qry.is_valid(code):
        qry.delete(code)


def test_get_type_choices():
    choices = qry.get_type_choices()
    assert isinstance(choices, dict)
    for proj_type in [qry.SOLO_BOOK, qry.COLLECTION, qry.ESSAY]:
        assert proj_type in choices


def test_is_valid_type():
    assert qry.is_valid_type(qry.ESSAY)
    assert not qry.is_valid_type('not a type')


def test_add(temp_project):
    assert isinstance(temp_project, str)
    proj = qry.fetch_by_key(temp_project)
    assert proj[qry.NAME] == qry.TEST_SAMPLE[qry.NAME]
    assert proj[qry.USER] == qry.TEST_SAMPLE[qry.USER]
    assert proj[qry.TYPE] == qry.TEST_SAMPLE[qry.TYPE]


def test_add_does_not_change_arg():
    sample = get_sample()
    code = qry.add(sample)
    assert qry.CODE not in sample
    qry.delete(code)


def test_add_same_name_twice():
    code1 = qry.add(get_sample())
    code2 = qry.add(get_sample())
    assert code1 != code2
    qry.delete(code1)
    qry.delete(code2)


@pytest.mark.parametrize('fld_nm', qry.REQUIRED_FLDS)
def test_add_missing_fld(fld_nm):
    sample = get_sample()
    del sample[fld_nm]
    with pytest.raises(ValueError):
        qry.add(sample)


@pytest.mark.parametrize('fld_nm', qry.REQUIRED_FLDS)
def test_add_blank_fld(fld_nm):
    sample = get_sample()
    sample[fld_nm] = '  '
    with pytest.raises(ValueError):
        qry.add(sample)


def test_add_bad_type():
    sample = get_sample()
    sample[qry.TYPE] = 'not a type'
    with pytest.raises(ValueError):
        qry.add(sample)


def test_fetch_list(temp_project):
    projects = qry.fetch_list()
    assert isinstance(projects, list)
    assert len(projects) > 0


def test_fetch_dict(temp_project):
    projects = qry.fetch_dict()
    assert isinstance(projects, dict)
    assert temp_project in projects


def test_fetch_codes(temp_project):
    codes = qry.fetch_codes()
    assert isinstance(codes, list)
    assert temp_project in codes


def test_get_choices(temp_project):
    assert temp_project in qry.get_choices()


def test_fetch_by_key_not_there():
    assert qry.fetch_by_key('A Very Unlikely Code') is None


def test_fetch_by_user(temp_project):
    projects = qry.fetch_by_user(qry.TEST_USER)
    assert temp_project in projects


def test_fetch_by_user_not_there():
    assert qry.fetch_by_user('no_such_user@example.com') == {}


def test_update(temp_project):
    NEW_NAME = 'A new name'
    qry.update(temp_project, {qry.NAME: NEW_NAME, qry.TYPE: qry.ESSAY})
    proj = qry.fetch_by_key(temp_project)
    assert proj[qry.NAME] == NEW_NAME
    assert proj[qry.TYPE] == qry.ESSAY
    assert proj[qry.USER] == qry.TEST_USER


def test_update_not_there():
    with pytest.raises(ValueError):
        qry.update('not an existing code', {qry.NAME: 'something'})


def test_update_bad_type(temp_project):
    with pytest.raises(ValueError):
        qry.update(temp_project, {qry.TYPE: 'not a type'})


def test_update_blank_name(temp_project):
    with pytest.raises(ValueError):
        qry.update(temp_project, {qry.NAME: ''})


def test_update_code(temp_project):
    with pytest.raises(ValueError):
        qry.update(temp_project, {qry.CODE: 'new code'})


def test_delete(temp_project):
    qry.delete(temp_project)
    assert qry.fetch_by_key(temp_project) is None


def test_delete_not_there():
    with pytest.raises(ValueError):
        qry.delete('not an existing code')
