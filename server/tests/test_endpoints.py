"""
This file contains the tests for our app's endpoints.
"""
from copy import deepcopy
from http import HTTPStatus
from unittest.mock import patch

import pytest

import server.endpoints as ep

TEST_CLIENT = ep.app.test_client()


def test_hello_get():
    """
    See if get request on Hello works.
    """
    resp_json = TEST_CLIENT.get(ep.HELLO).get_json()
    assert isinstance(resp_json['message'], str)


def test_hello_post():
    """
    See if post request on Hello works.
    """
    resp_json = TEST_CLIENT.post(ep.HELLO).get_json()
    assert isinstance(resp_json['message'], str)


def test_endpoints_map():
    """
    Test that the endpoint map is a dictionary.
    """
    resp_json = TEST_CLIENT.get(f'{ep.ENDPOINTS}/{ep.MAP}').get_json()
    assert isinstance(resp_json[ep.EP_READ_KEY], dict)


TEST_AUTH_KEY = 'a test auth key'
AUTH_HDRS = {ep.AUTH_KEY: TEST_AUTH_KEY}
USER_PARAM = {ep.pqry.USER: ep.pqry.TEST_USER}
NEW_PROJECT = {ep.pqry.NAME: 'An Endpoint Project',
               ep.pqry.TYPE: ep.pqry.ESSAY}
NO_SUCH_CODE = 'not an existing code'


@pytest.fixture(scope='function')
def temp_project():
    code = ep.pqry.add(deepcopy(ep.pqry.TEST_SAMPLE))
    yield code
    if ep.pqry.is_valid(code):
        ep.pqry.delete(code)


def test_check_access():
    with ep.app.test_request_context(query_string=USER_PARAM,
                                     headers=AUTH_HDRS):
        assert ep.check_access(ep.request) == ep.pqry.TEST_USER


def test_projects_no_user():
    resp = TEST_CLIENT.get(ep.PROJ_READ_W_NS, headers=AUTH_HDRS)
    assert resp.status_code == HTTPStatus.BAD_REQUEST


def test_projects_no_auth_key():
    resp = TEST_CLIENT.get(ep.PROJ_READ_W_NS, query_string=USER_PARAM)
    assert resp.status_code == HTTPStatus.UNAUTHORIZED


@patch('server.security.is_allowed', return_value=False, autospec=True)
def test_projects_not_allowed(mock_is_allowed):
    resp = TEST_CLIENT.get(ep.PROJ_READ_W_NS, query_string=USER_PARAM,
                           headers=AUTH_HDRS)
    assert resp.status_code == HTTPStatus.FORBIDDEN
    mock_is_allowed.assert_called_once_with(ep.pqry.TEST_USER, TEST_AUTH_KEY)


def test_fetch_project(temp_project):
    assert ep.fetch_project(temp_project)[ep.CODE] == temp_project


def test_fetch_project_not_there():
    with pytest.raises(ep.wz.NotFound):
        ep.fetch_project(NO_SUCH_CODE)


def test_project_create():
    resp = TEST_CLIENT.post(ep.PROJ_CREATE_W_NS, json=NEW_PROJECT,
                            query_string=USER_PARAM, headers=AUTH_HDRS)
    assert resp.status_code == HTTPStatus.OK
    code = resp.get_json()[ep.CODE]
    project = ep.pqry.fetch_by_key(code)
    assert project[ep.pqry.NAME] == NEW_PROJECT[ep.pqry.NAME]
    assert project[ep.pqry.USER] == ep.pqry.TEST_USER
    ep.pqry.delete(code)


def test_project_create_bad_type():
    bad_project = {**NEW_PROJECT, ep.pqry.TYPE: 'not a type'}
    resp = TEST_CLIENT.post(ep.PROJ_CREATE_W_NS, json=bad_project,
                            query_string=USER_PARAM, headers=AUTH_HDRS)
    assert resp.status_code == HTTPStatus.NOT_ACCEPTABLE


def test_projects_read(temp_project):
    resp = TEST_CLIENT.get(ep.PROJ_READ_W_NS, query_string=USER_PARAM,
                           headers=AUTH_HDRS)
    assert resp.status_code == HTTPStatus.OK
    assert temp_project in resp.get_json()[ep.PROJECTS_READ]


def test_project_retrieve(temp_project):
    resp = TEST_CLIENT.get(f'{ep.PROJ_RETRIEVE_W_NS}/{temp_project}',
                           query_string=USER_PARAM, headers=AUTH_HDRS)
    assert resp.status_code == HTTPStatus.OK
    assert resp.get_json()[ep.CODE] == temp_project


def test_project_retrieve_not_there():
    resp = TEST_CLIENT.get(f'{ep.PROJ_RETRIEVE_W_NS}/{NO_SUCH_CODE}',
                           query_string=USER_PARAM, headers=AUTH_HDRS)
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_project_update(temp_project):
    new_name = 'A new name'
    resp = TEST_CLIENT.put(f'{ep.PROJ_UPDATE_W_NS}/{temp_project}',
                           json={ep.pqry.NAME: new_name},
                           query_string=USER_PARAM, headers=AUTH_HDRS)
    assert resp.status_code == HTTPStatus.OK
    assert ep.pqry.fetch_by_key(temp_project)[ep.pqry.NAME] == new_name


def test_project_update_not_there():
    resp = TEST_CLIENT.put(f'{ep.PROJ_UPDATE_W_NS}/{NO_SUCH_CODE}',
                           json={ep.pqry.NAME: 'A new name'},
                           query_string=USER_PARAM, headers=AUTH_HDRS)
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_project_update_bad_type(temp_project):
    resp = TEST_CLIENT.put(f'{ep.PROJ_UPDATE_W_NS}/{temp_project}',
                           json={ep.pqry.TYPE: 'not a type'},
                           query_string=USER_PARAM, headers=AUTH_HDRS)
    assert resp.status_code == HTTPStatus.NOT_ACCEPTABLE


def test_project_delete(temp_project):
    resp = TEST_CLIENT.delete(f'{ep.PROJ_DELETE_W_NS}/{temp_project}',
                              query_string=USER_PARAM, headers=AUTH_HDRS)
    assert resp.status_code == HTTPStatus.OK
    assert ep.pqry.fetch_by_key(temp_project) is None


def test_project_delete_not_there():
    resp = TEST_CLIENT.delete(f'{ep.PROJ_DELETE_W_NS}/{NO_SUCH_CODE}',
                              query_string=USER_PARAM, headers=AUTH_HDRS)
    assert resp.status_code == HTTPStatus.NOT_FOUND
