"""Requirements API uses editor authentication and write protections."""
import base64

import pytest

from projects import query as qry
from server.endpoints import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setitem(app.config, 'EDITOR_USERNAME', 'editor')
    monkeypatch.setitem(app.config, 'EDITOR_PASSWORD', 'test-password')
    client = app.test_client()
    token = base64.b64encode(b'editor:test-password').decode()
    client.environ_base['HTTP_AUTHORIZATION'] = f'Basic {token}'
    return client


@pytest.fixture
def books():
    codes = [qry.add({**qry.TEST_SAMPLE, qry.TYPE: qry.COLLECTION})
             for _ in range(2)]
    yield codes
    for code in codes:
        qry.delete(code)


def endpoint(code):
    return f'/api/editor/projects/{code}/requirements'


def test_save_read_and_project_isolation(client, books):
    first, second = books
    flags = dict.fromkeys(qry.REQUIREMENT_FIELDS, True)
    assert client.post(endpoint(first), json=flags).json == {
        'requirements': flags}
    qry.get_cache(qry.COLLECT).clear_cache()
    assert client.get(endpoint(first)).json == {'requirements': flags}
    assert client.get(endpoint(second)).json == {
        'requirements': dict.fromkeys(qry.REQUIREMENT_FIELDS, False)}
    response = client.post(endpoint(first), json={qry.REQUIRES_BIO: False})
    assert response.status_code == 200
    assert response.json['requirements'] == {**flags, qry.REQUIRES_BIO: False}


@pytest.mark.parametrize('payload', [
    {}, [], {'name': 'Not allowed'}, {'requires_bio': 'false'},
    {'requires_address': 1}, {'requires_permission': None},
])
def test_invalid_requests_do_not_change_project(client, books, payload):
    before = qry.fetch_by_key(books[0])
    assert client.post(endpoint(books[0]), json=payload).status_code == 400
    assert qry.fetch_by_key(books[0]) == before


def test_editor_access_and_cross_origin(client, books):
    url = endpoint(books[0])
    assert client.get(url, headers={'Authorization': ''}).status_code == 401
    assert client.post(url, json={qry.REQUIRES_BIO: True},
                       headers={'Authorization': ''}).status_code == 401
    assert client.post(url, json={qry.REQUIRES_BIO: True},
                       headers={'Origin': 'https://other.example'}
                       ).status_code == 403
    assert client.post(url, data='requires_bio=true').status_code == 415
    assert qry.fetch_by_key(books[0])[qry.REQUIRES_BIO] is False


def test_missing_and_wrong_type(client):
    assert client.get(endpoint('missing')).status_code == 404
    assert client.post(endpoint('missing'), json={qry.REQUIRES_BIO: True}
                       ).status_code == 404
    code = qry.add(qry.TEST_SAMPLE)
    try:
        assert client.get(endpoint(code)).status_code == 400
        assert client.post(endpoint(code), json={qry.REQUIRES_BIO: True}
                           ).status_code == 400
    finally:
        qry.delete(code)
