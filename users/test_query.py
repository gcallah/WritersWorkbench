from copy import deepcopy

import pytest

import users.query as qry


def get_sample():
    return deepcopy(qry.TEST_SAMPLE)


@pytest.fixture(scope='function')
def temp_user():
    user_id = qry.add(get_sample())
    yield user_id
    if qry.is_valid(user_id):
        qry.delete(user_id)


def test_add(temp_user):
    assert isinstance(temp_user, str)
    user = qry.fetch_by_key(temp_user)
    assert user[qry.NAME] == qry.TEST_SAMPLE[qry.NAME]
    assert user[qry.AUTH_KEY] == qry.TEST_SAMPLE[qry.AUTH_KEY]
    assert user[qry.ID] == temp_user


def test_add_does_not_change_arg():
    sample = get_sample()
    user_id = qry.add(sample)
    assert qry.ID not in sample
    qry.delete(user_id)


def test_add_same_name_twice_gets_unique_ids():
    id1 = qry.add(get_sample())
    id2 = qry.add(get_sample())
    assert id1 != id2
    qry.delete(id1)
    qry.delete(id2)


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


def test_fetch_by_key_not_there():
    assert qry.fetch_by_key('A Very Unlikely Id') is None


def test_fetch_list(temp_user):
    users = qry.fetch_list()
    assert isinstance(users, list)
    assert len(users) > 0


def test_fetch_dict(temp_user):
    users = qry.fetch_dict()
    assert isinstance(users, dict)
    assert temp_user in users


def test_update(temp_user):
    qry.update(temp_user, {qry.NAME: 'New Name', qry.AUTH_KEY: 'new-key'})
    user = qry.fetch_by_key(temp_user)
    assert user[qry.NAME] == 'New Name'
    assert user[qry.AUTH_KEY] == 'new-key'


def test_update_not_there():
    with pytest.raises(ValueError):
        qry.update('not an existing id', {qry.NAME: 'something'})


def test_update_blank_name(temp_user):
    with pytest.raises(ValueError):
        qry.update(temp_user, {qry.NAME: ''})


def test_update_id(temp_user):
    with pytest.raises(ValueError):
        qry.update(temp_user, {qry.ID: 'new id'})


def test_delete(temp_user):
    qry.delete(temp_user)
    assert qry.fetch_by_key(temp_user) is None


def test_delete_not_there():
    with pytest.raises(ValueError):
        qry.delete('not an existing id')
