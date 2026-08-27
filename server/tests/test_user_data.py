"""
Tests for user endpoints.
"""
from copy import deepcopy
from http import HTTPStatus
import random

from unittest.mock import patch
import pytest

from http.client import (
    CONFLICT,
    NOT_ACCEPTABLE,
    OK,
)

from backendcore.security.auth_key import create_auth_key_hdr
import backendcore.security.password as pw
import backendcore.users.query as usr

import server.endpoints as ep

TEST_CLIENT = ep.app.test_client()

# big enough we're never going to get it twice in our lives:
BIG_INT = 1000000000


def gen_email():
    return f'name{str(random.randint(0, BIG_INT))}@erols.com'


def signup_w_email(email=None):
    args = deepcopy(ep.SAMPLE_SIGNUP_FLDS)
    args[ep.EMAIL] = gen_email() if not email else email
    return args


@pytest.fixture
def a_user_email():
    """
    Creates a user and returns the user's email.
    """
    args = signup_w_email()
    ep.signup(args[ep.EMAIL], args[ep.PASSWORD], args[ep.FIRST_NAME],
              args[ep.LAST_NAME], args.get(ep.ORG))
    yield args[ep.EMAIL]
    usr.del_user(args[ep.EMAIL])


another_user_email = a_user_email


def test_signup():
    """
    Tests if a signup that ought to be good is successful.
    We must get an auth_key back.
    """
    args = signup_w_email()
    resp = TEST_CLIENT.post(ep.SIGNUP_W_NS, json=args)
    assert resp.status_code == OK
    assert ep.AUTH_KEY in resp.json
    assert isinstance(resp.json[ep.AUTH_KEY], str)


def test_signup_dup_user(a_user_email):
    args = signup_w_email(email=a_user_email)
    resp = TEST_CLIENT.post(ep.SIGNUP_W_NS, json=args)
    assert resp.status_code == CONFLICT


def test_login_success(a_user_email):
    """
    Tests if a login that ought to be good is successful.
    We must get an auth_key back.
    """
    email = a_user_email
    login_flds = {
        ep.EMAIL: email,
        ep.PASSWORD: ep.SAMPLE_PASSWORD,
    }
    resp = TEST_CLIENT.post(ep.LOGIN_W_NS, json=login_flds)
    assert resp.status_code == OK
    assert ep.AUTH_KEY in resp.json
    assert isinstance(resp.json[ep.AUTH_KEY], str)


def test_login_failure(a_user_email):
    """
    A bad password should give us a failed login.
    """
    email = a_user_email
    login_flds = {
        ep.EMAIL: email,
        ep.PASSWORD: 'incorrect_password',
    }
    resp = TEST_CLIENT.post(ep.LOGIN_W_NS, json=login_flds)
    assert resp.status_code == HTTPStatus.UNAUTHORIZED


@patch('backendcore.emailer.pw_reset.send_email', return_value=True,
       autospec=True)
def test_req_pw_reset(patch_send_email, a_user_email):
    """
    Test if a registered email can request a password reset.
    """
    resp = TEST_CLIENT.get(f'{ep.PW_RESET_TOK_W_NS}/{a_user_email}')
    print(resp.data)
    assert resp.status_code == OK


def test_req_pw_reset_not_ok():
    """
    An invalid email should fail a password reset request.
    """
    resp = TEST_CLIENT.get(f'{ep.PW_RESET_TOK_W_NS}/bad_email')
    assert resp.status_code == NOT_ACCEPTABLE


def test_pw_reset_ok(a_user_email):
    """
    Tests if a password reset request with a properly created reset token works
    """
    email = a_user_email
    tok = pw.create_pw_reset_token(email)
    reset_flds = {
        ep.USER_ID: email,
        ep.NEW_PW: 'test',
        ep.PW_RESET_TOK: tok,
    }
    resp = TEST_CLIENT.patch(ep.RESET_PW_W_NS, json=reset_flds)
    assert resp.status_code == OK


def test_pw_reset_bad_email(a_user_email):
    """
    Tests if a password reset request with an invalid email fails
    """
    email = a_user_email
    tok = pw.create_pw_reset_token(email)
    reset_flds = {
        ep.USER_ID: 'invalid email',
        ep.NEW_PW: 'test',
        ep.PW_RESET_TOK: tok,
    }
    resp = TEST_CLIENT.patch(ep.RESET_PW_W_NS, json=reset_flds)
    assert resp.status_code == NOT_ACCEPTABLE


def test_pw_reset_bad_token(a_user_email):
    """
    Tests if a password reset request with an invalid email fails
    """
    email = a_user_email
    pw.create_pw_reset_token(email)
    reset_flds = {
        ep.USER_ID: email,
        ep.NEW_PW: 'test',
        ep.PW_RESET_TOK: 'invalid_token',
    }
    resp = TEST_CLIENT.patch(ep.RESET_PW_W_NS, json=reset_flds)
    assert resp.status_code == NOT_ACCEPTABLE


def test_pw_reset_other_token(a_user_email, another_user_email):
    """
    Tests if a password reset request with a different users reset token fails
    """
    email1 = a_user_email
    email2 = another_user_email
    pw.create_pw_reset_token(email1)
    tok2 = pw.create_pw_reset_token(email2)
    reset_flds = {
        ep.USER_ID: email1,
        ep.NEW_PW: 'test',
        ep.PW_RESET_TOK: tok2,
    }
    resp = TEST_CLIENT.patch(ep.RESET_PW_W_NS, json=reset_flds)
    assert resp.status_code == NOT_ACCEPTABLE


def test_valid_key(a_user_email):
    """
    Tests if the auth_key returned from a login returns a valid key
    """
    login_flds = {
        ep.EMAIL: a_user_email,
        ep.PASSWORD: ep.SAMPLE_PASSWORD,
    }
    auth_key = TEST_CLIENT.post(ep.LOGIN_W_NS, json=login_flds).json
    resp = TEST_CLIENT.get(ep.VALID_KEY_W_NS, json={ep.USER_ID: a_user_email},
                           headers=auth_key)
    assert resp.status_code == OK


def test_missing_valid_key(a_user_email):
    """
    Tests if the sending a request to key validation without a key
    in the header returns UNAUTHORIZED
    """
    resp = TEST_CLIENT.get(ep.VALID_KEY_W_NS)
    assert resp.status_code == HTTPStatus.UNAUTHORIZED


def test_invalid_key(a_user_email):
    """
    Tests if the auth_key returned from a login returns a valid key
    """
    resp = TEST_CLIENT.get(ep.VALID_KEY_W_NS,
                           headers=create_auth_key_hdr('invalid key'),
                           json={ep.USER_ID: a_user_email})
    assert resp.status_code == HTTPStatus.UNAUTHORIZED
