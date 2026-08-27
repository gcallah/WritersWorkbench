"""
This file contains the tests for our app's endpoints.
"""
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
