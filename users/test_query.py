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


def test_password_is_hashed_and_verified(temp_user):
    stored = qry.get_cache(qry.COLLECT).fetch_by_key(temp_user)
    assert qry.PASSWORD not in stored
    assert stored[qry.PASSWORD_HASH] != qry.TEST_SAMPLE[qry.PASSWORD]
    assert qry.check_password(temp_user, qry.TEST_SAMPLE[qry.PASSWORD])
    assert not qry.check_password(temp_user, 'wrong-password')


def test_reads_hide_passwords_without_changing_storage(temp_user):
    before = qry.get_cache(qry.COLLECT).fetch_by_key(temp_user)
    records = [qry.fetch_by_key(temp_user),
               qry.fetch_dict()[temp_user]] + qry.fetch_list()
    for record in records:
        assert qry.PASSWORD not in record
        assert qry.PASSWORD_HASH not in record
    assert qry.get_cache(qry.COLLECT).fetch_by_key(temp_user) == before


def test_password_change_preserves_input(temp_user):
    changes = {qry.PASSWORD: 'new-test-password'}
    original = dict(changes)
    qry.update(temp_user, changes)
    assert changes == original
    assert qry.check_password(temp_user, 'new-test-password')
    assert not qry.check_password(temp_user, qry.TEST_SAMPLE[qry.PASSWORD])


def test_name_change_preserves_password(temp_user):
    qry.update(temp_user, {qry.NAME: 'Another Name'})
    assert qry.check_password(temp_user, qry.TEST_SAMPLE[qry.PASSWORD])


@pytest.mark.parametrize('password', [None, '', '   ', 123, [], {}])
def test_invalid_password_update_preserves_existing(temp_user, password):
    with pytest.raises(ValueError):
        qry.update(temp_user, {qry.PASSWORD: password})
    assert qry.check_password(temp_user, qry.TEST_SAMPLE[qry.PASSWORD])


@pytest.mark.parametrize('password', [None, '', '   ', 123, [], {}])
def test_invalid_password_create(password):
    sample = get_sample()
    sample[qry.PASSWORD] = password
    with pytest.raises(ValueError):
        qry.add(sample)


def test_cannot_supply_hash_directly(temp_user):
    with pytest.raises(ValueError):
        qry.update(temp_user, {qry.PASSWORD_HASH: 'injected-hash'})
    sample = get_sample()
    sample[qry.PASSWORD_HASH] = 'injected-hash'
    with pytest.raises(ValueError):
        qry.add(sample)
    assert qry.check_password(temp_user, qry.TEST_SAMPLE[qry.PASSWORD])


@pytest.mark.parametrize('password', [None, '', '   ', 123])
def test_invalid_password_check(temp_user, password):
    assert not qry.check_password(temp_user, password)


def test_missing_user_cannot_authenticate():
    assert not qry.check_password('missing-user', 'some-password')


@pytest.fixture
def legacy_user():
    from uuid import uuid4
    user_id = uuid4().hex
    # Insert the old record shape directly, as it predates password support.
    qry.fetch_list()
    qry.get_cache(qry.COLLECT).add({
        qry.ID: user_id, qry.NAME: 'Legacy User', qry.AUTH_KEY: 'old-key',
    })
    yield user_id
    if qry.is_valid(user_id):
        qry.delete(user_id)


def test_legacy_user_remains_usable(legacy_user):
    assert qry.fetch_by_key(legacy_user)[qry.NAME] == 'Legacy User'
    assert not qry.check_password(legacy_user, 'any-password')
    qry.update(legacy_user, {qry.NAME: 'Updated Legacy User'})
    assert qry.fetch_by_key(legacy_user)[qry.NAME] == 'Updated Legacy User'
    assert not qry.check_password(legacy_user, 'any-password')
    qry.update(legacy_user, {qry.PASSWORD: 'first-password'})
    assert qry.check_password(legacy_user, 'first-password')
    qry.delete(legacy_user)
    assert qry.fetch_by_key(legacy_user) is None


def test_same_password_has_different_salts(temp_user):
    other_id = qry.add(get_sample())
    try:
        cache = qry.get_cache(qry.COLLECT)
        assert (cache.fetch_by_key(temp_user)[qry.PASSWORD_HASH]
                != cache.fetch_by_key(other_id)[qry.PASSWORD_HASH])
    finally:
        qry.delete(other_id)


def test_add_preserves_password_input():
    sample = get_sample()
    original = deepcopy(sample)
    user_id = qry.add(sample)
    try:
        assert sample == original
    finally:
        qry.delete(user_id)


def test_legacy_import_preserves_ids_and_does_not_overwrite(monkeypatch):
    from uuid import uuid4
    from users import migrate_legacy
    user_id = uuid4().hex
    old = {qry.ID: user_id, qry.NAME: 'Old App User', qry.AUTH_KEY: 'key'}
    # Simulate both an old application record and an unrelated login record.
    original_fetch = migrate_legacy.dbc.fetch_all

    def legacy_source(db, collection, **kwargs):
        if collection in ('Users', 'users'):
            return [dict(old), {'email': 'old@x'}]
        return original_fetch(db, collection, **kwargs)

    monkeypatch.setattr(migrate_legacy.dbc, 'fetch_all', legacy_source)
    try:
        assert migrate_legacy.migrate() == 1
        assert qry.fetch_by_key(user_id)[qry.NAME] == 'Old App User'
        assert not qry.check_password(user_id, 'anything')
        qry.update(user_id, {qry.NAME: 'Changed'})
        assert migrate_legacy.migrate() == 0
        assert qry.fetch_by_key(user_id)[qry.NAME] == 'Changed'
    finally:
        if qry.is_valid(user_id):
            qry.delete(user_id)
