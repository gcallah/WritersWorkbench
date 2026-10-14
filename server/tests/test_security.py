import server.security as sec


def test_is_allowed():
    assert sec.is_allowed('some_user@example.com', 'some auth key')
