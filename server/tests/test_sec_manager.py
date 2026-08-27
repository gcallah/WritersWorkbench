from http.client import (
    NOT_FOUND,
    OK,
)

from unittest.mock import patch

from backendcore.security.sec_manager2 import GOOD_PROTOCOL

import server.endpoints as ep

TEST_CLIENT = ep.app.test_client()

SEC_MANAGER = 'backendcore.security.sec_manager2'


@patch(f"{SEC_MANAGER}.fetch_by_key", autospec=True,
       return_value=GOOD_PROTOCOL)
def test_retrieve_protocol(mock_fetch_by_key):
    """
    Can we successfully fetch a protocol?
    """
    resp = TEST_CLIENT.get(f'{ep.SEC_MANAGER_RETRIEVE_W_NS}/a_good_protocol')
    assert resp.status_code == OK


@patch(f"{SEC_MANAGER}.fetch_by_key", autospec=True, return_value=None)
def test_retrieve_protocol_not_there(mock_fetch_by_key):
    """
    Do we return NOT_FOUND when trying to fetch a protocol that
    does not exist?
    """
    resp = TEST_CLIENT.get(f'{ep.SEC_MANAGER_RETRIEVE_W_NS}/a_bad_protocol')
    assert resp.status_code == NOT_FOUND


@patch(f"{SEC_MANAGER}.is_permitted", autospec=True, return_value=True)
def test_security_manager_is_permitted(mock_is_valid_user):
    url = ep.SEC_MANAGER_IS_PERMITTED_W_NS
    resp = TEST_CLIENT.get(f'{url}/a_protocol/a_action/a_user')
    assert resp.status_code == OK
    assert resp.json[ep.IS_PERMITTED]


@patch(f"{SEC_MANAGER}.is_permitted", autospec=True, return_value=False)
def test_security_manager_is_not_permitted(mock_is_valid_user):
    url = ep.SEC_MANAGER_IS_PERMITTED_W_NS
    print(f'{url=}')
    resp = TEST_CLIENT.get(f'{url}/a_protocol/a_action/invalid_user')
    assert resp.status_code == OK
    assert not resp.json[ep.IS_PERMITTED]
