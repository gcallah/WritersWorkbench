"""Project requirements must not be confused with received submissions."""
from uuid import uuid4

import pytest

from projects import query as qry


@pytest.fixture
def volume():
    code = qry.add({**qry.TEST_SAMPLE, qry.TYPE: qry.COLLECTION})
    yield code
    if qry.is_valid(code):
        qry.delete(code)


def test_new_defaults_and_input_unchanged():
    sample = {**qry.TEST_SAMPLE, qry.TYPE: qry.COLLECTION}
    original = dict(sample)
    code = qry.add(sample)
    try:
        assert sample == original
        record = qry.fetch_by_key(code)
        assert all(record[f] is False for f in qry.REQUIREMENT_FIELDS)
    finally:
        qry.delete(code)


@pytest.mark.parametrize('field', qry.REQUIREMENT_FIELDS)
def test_requirement_round_trip(volume, field):
    qry.update(volume, {field: True})
    qry.get_cache(qry.COLLECT).clear_cache()
    assert qry.fetch_by_key(volume)[field] is True
    qry.update(volume, {qry.NAME: 'Renamed'})
    assert qry.fetch_by_key(volume)[field] is True
    qry.update(volume, {field: False})
    assert qry.fetch_by_key(volume)[field] is False


@pytest.mark.parametrize('field', qry.REQUIREMENT_FIELDS)
@pytest.mark.parametrize('value', ['false', 'true', 0, 1, None, [], {}])
def test_reject_non_boolean_create_and_update(volume, field, value):
    with pytest.raises(ValueError, match='true or false'):
        qry.add({**qry.TEST_SAMPLE, field: value})
    with pytest.raises(ValueError, match='true or false'):
        qry.update(volume, {field: value, qry.NAME: 'Must not change'})
    assert qry.fetch_by_key(volume)[qry.NAME] == qry.TEST_SAMPLE[qry.NAME]


def test_create_with_requirements():
    code = qry.add({**qry.TEST_SAMPLE,
                    **dict.fromkeys(qry.REQUIREMENT_FIELDS, True)})
    try:
        assert all(qry.fetch_by_key(code)[f] is True
                   for f in qry.REQUIREMENT_FIELDS)
    finally:
        qry.delete(code)


def test_legacy_records_default_in_every_read(volume):
    code = uuid4().hex
    cache = qry.get_cache(qry.COLLECT)
    cache.add({**qry.TEST_SAMPLE, qry.CODE: code})
    try:
        records = [qry.fetch_by_key(code), qry.fetch_dict()[code],
                   qry.fetch_by_user(qry.TEST_USER)[code]]
        records += [p for p in qry.fetch_list() if p[qry.CODE] == code]
        for record in records:
            assert all(record[f] is False for f in qry.REQUIREMENT_FIELDS)
        assert qry.fetch_by_key('missing-project') is None
        qry.update(code, {qry.REQUIRES_BIO: True})
        assert qry.fetch_by_key(code)[qry.REQUIRES_BIO] is True
    finally:
        qry.delete(code)
