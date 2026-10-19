"""
This file contains the tests for our app's endpoints.
"""
from copy import deepcopy
from http import HTTPStatus
from unittest.mock import patch
from uuid import uuid4

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


def test_endpoints_read_preserves_routes_and_methods():
    response = TEST_CLIENT.get(f'/{ep.ENDPOINTS}/{ep.READ}')
    assert response.status_code == HTTPStatus.OK
    endpoint_docs = response.get_json()[ep.ENDPOINT_STR]
    assert set(endpoint_docs[f'/{ep.HELLO}']) == {'get', 'post'}
    assert set(endpoint_docs['/editor']) == {'get'}
    assert set(endpoint_docs['/api/contributors']) == {'get', 'post'}
    assert all(endpoint_docs[f'/{ep.HELLO}'].values())
    assert endpoint_docs['/editor']['get']
    assert not {'/', '/swagger.json', '/swaggerui/<path:filename>',
                '/static/<path:filename>'}.intersection(endpoint_docs)


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


OWNER_HDRS = {ep.AUTH_KEY: ep.uqry.TEST_SAMPLE[ep.uqry.AUTH_KEY]}
STRANGER_HDRS = {ep.AUTH_KEY: 'someone else'}
NO_SUCH_ID = 'not an existing id'


@pytest.fixture(scope='function')
def temp_user():
    user_id = ep.uqry.add(deepcopy(ep.uqry.TEST_SAMPLE))
    yield user_id
    if ep.uqry.is_valid(user_id):
        ep.uqry.delete(user_id)


def test_user_create():
    resp = TEST_CLIENT.post(ep.USER_CREATE_W_NS,
                            json=ep.uqry.TEST_SAMPLE,
                            query_string=USER_PARAM, headers=AUTH_HDRS)
    assert resp.status_code == HTTPStatus.OK
    ep.uqry.delete(resp.get_json()[ep.uqry.ID])


def test_user_create_no_password():
    no_pw = {key: val for key, val in ep.uqry.TEST_SAMPLE.items()
             if key != ep.uqry.PASSWORD}
    resp = TEST_CLIENT.post(ep.USER_CREATE_W_NS, json=no_pw,
                            query_string=USER_PARAM, headers=AUTH_HDRS)
    assert resp.status_code == HTTPStatus.NOT_ACCEPTABLE


def test_user_retrieve_hides_auth_key(temp_user):
    resp = TEST_CLIENT.get(f'{ep.USER_RETRIEVE_W_NS}/{temp_user}',
                           query_string=USER_PARAM, headers=AUTH_HDRS)
    assert resp.status_code == HTTPStatus.OK
    assert ep.uqry.AUTH_KEY not in resp.get_json()


def test_user_update_by_stranger(temp_user):
    resp = TEST_CLIENT.put(f'{ep.USER_UPDATE_W_NS}/{temp_user}',
                           json={ep.uqry.NAME: 'Hacked'},
                           query_string=USER_PARAM, headers=STRANGER_HDRS)
    assert resp.status_code == HTTPStatus.FORBIDDEN


def test_user_password_change(temp_user):
    resp = TEST_CLIENT.put(
        f'{ep.USER_UPDATE_W_NS}/{temp_user}',
        json={ep.uqry.PASSWORD: 'a new password',
              ep.CURRENT_PW: ep.uqry.TEST_SAMPLE[ep.uqry.PASSWORD]},
        query_string=USER_PARAM, headers=OWNER_HDRS)
    assert resp.status_code == HTTPStatus.OK
    assert ep.uqry.check_password(temp_user, 'a new password')


def test_users_read_hides_auth_keys(temp_user):
    resp = TEST_CLIENT.get(ep.USER_READ_W_NS, query_string=USER_PARAM,
                           headers=AUTH_HDRS)
    assert resp.status_code == HTTPStatus.OK
    users = resp.get_json()[ep.USERS_READ]
    assert temp_user in users
    for user in users.values():
        assert ep.uqry.AUTH_KEY not in user


def test_user_retrieve_not_there():
    resp = TEST_CLIENT.get(f'{ep.USER_RETRIEVE_W_NS}/{NO_SUCH_ID}',
                           query_string=USER_PARAM, headers=AUTH_HDRS)
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_fetch_user_not_there():
    with pytest.raises(ep.wz.NotFound):
        ep.fetch_user(NO_SUCH_ID)


def test_check_owner_wrong_key(temp_user):
    with ep.app.test_request_context(headers=STRANGER_HDRS):
        with pytest.raises(ep.wz.Forbidden):
            ep.check_owner(ep.request, ep.fetch_user(temp_user))


def test_user_password_change_wrong_current(temp_user):
    resp = TEST_CLIENT.put(
        f'{ep.USER_UPDATE_W_NS}/{temp_user}',
        json={ep.uqry.PASSWORD: 'a new password',
              ep.CURRENT_PW: 'the wrong password'},
        query_string=USER_PARAM, headers=OWNER_HDRS)
    assert resp.status_code == HTTPStatus.FORBIDDEN
    assert ep.uqry.check_password(temp_user,
                                  ep.uqry.TEST_SAMPLE[ep.uqry.PASSWORD])


def test_user_delete(temp_user):
    resp = TEST_CLIENT.delete(f'{ep.USER_DELETE_W_NS}/{temp_user}',
                              query_string=USER_PARAM, headers=OWNER_HDRS)
    assert resp.status_code == HTTPStatus.OK
    assert ep.uqry.fetch_by_key(temp_user) is None


@patch('users.query.delete', autospec=True)
def test_user_delete_by_stranger(mock_delete, temp_user):
    resp = TEST_CLIENT.delete(f'{ep.USER_DELETE_W_NS}/{temp_user}',
                              query_string=USER_PARAM, headers=STRANGER_HDRS)
    assert resp.status_code == HTTPStatus.FORBIDDEN
    mock_delete.assert_not_called()


LEGACY_HDRS = {ep.AUTH_KEY: 'legacy-auth-key'}


@pytest.fixture(scope='function')
def legacy_user():
    """
    A user saved before passwords existed, so it has no password hash.
    """
    user_id = uuid4().hex
    ep.uqry.fetch_list()  # makes sure the users cache is loaded
    ep.uqry.get_cache(ep.uqry.COLLECT).add({
        ep.uqry.ID: user_id,
        ep.uqry.NAME: 'Legacy User',
        ep.uqry.AUTH_KEY: LEGACY_HDRS[ep.AUTH_KEY],
    })
    yield user_id
    if ep.uqry.is_valid(user_id):
        ep.uqry.delete(user_id)


def test_legacy_user_sets_first_password(legacy_user):
    resp = TEST_CLIENT.put(f'{ep.USER_UPDATE_W_NS}/{legacy_user}',
                           json={ep.uqry.PASSWORD: 'first password'},
                           query_string=USER_PARAM, headers=LEGACY_HDRS)
    assert resp.status_code == HTTPStatus.OK
    assert ep.uqry.check_password(legacy_user, 'first password')


def test_legacy_password_by_stranger(legacy_user):
    resp = TEST_CLIENT.put(f'{ep.USER_UPDATE_W_NS}/{legacy_user}',
                           json={ep.uqry.PASSWORD: 'hijacked'},
                           query_string=USER_PARAM, headers=STRANGER_HDRS)
    assert resp.status_code == HTTPStatus.FORBIDDEN
