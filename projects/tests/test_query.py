from copy import deepcopy

import pytest

import projects.query as qry


def del_test_item(code):
    """
    Delete by code.
    """
    return qry.delete(code)


def get_sample():
    return deepcopy(qry.TEST_SAMPLE)


def add_test_sample():
    return qry.add(get_sample())


@pytest.fixture(scope='function')
def temp_sample():
    try:  # in case some failed test left it hanging on...
        del_test_item(qry.TEST_CODE)
    except Exception:
        print(f'{qry.TEST_CODE} was not present')
    sample_dict = deepcopy(qry.TEST_SAMPLE)
    ret = qry.add(sample_dict)
    yield ret
    del_test_item(qry.TEST_CODE)


@pytest.fixture(scope='function')
def new_sample():
    """
    Creates a entry, but does not delete it after test runs.
    """
    return add_test_sample()


def test_fetch_codes(temp_sample):
    codes = qry.fetch_codes()
    assert isinstance(codes, list)
    assert qry.TEST_CODE in codes


def test_fetch_list(temp_sample):
    samples = qry.fetch_list()
    assert isinstance(samples, list)
    assert len(samples) > 0


def test_fetch_dict(temp_sample):
    samples = qry.fetch_dict()
    assert isinstance(samples, dict)
    assert len(samples) > 0


def test_get_choices(temp_sample):
    choices = qry.get_choices()
    assert qry.TEST_CODE in choices


def test_fetch_by_key(temp_sample):
    entry = qry.fetch_by_key(qry.TEST_CODE)
    assert entry[qry.CODE] == qry.TEST_CODE


def test_fetch_by_key_not_there():
    assert qry.fetch_by_key('A Very Unlikely Term') is None


def test_add():
    qry.add(get_sample())
    assert qry.fetch_by_key(qry.TEST_CODE) is not None
    del_test_item(qry.TEST_CODE)


def test_add_dup_term(temp_sample):
    with pytest.raises(ValueError):
        qry.add(get_sample())


def test_delete(new_sample):
    qry.delete(qry.TEST_CODE)
    assert qry.fetch_by_key(qry.TEST_CODE) is None


def test_delete_not_there():
    with pytest.raises(ValueError):
        qry.delete('not an existing code')


def test_update(temp_sample):
    NEW_NAME = 'A new name'
    update_dict = {qry.NAME: NEW_NAME}
    assert qry.fetch_by_key(qry.TEST_CODE)[qry.NAME] != NEW_NAME
    qry.update(qry.TEST_CODE, update_dict)
    assert qry.fetch_by_key(qry.TEST_CODE)[qry.NAME] == NEW_NAME


def test_update_not_there():
    update_dict = {qry.NAME: 'something'}
    with pytest.raises(ValueError):
        qry.update('not an existing code', update_dict)
