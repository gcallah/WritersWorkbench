"""The editor adds a table of contents by uploading a markdown file."""
import base64
from io import BytesIO

import pytest

from projects import query as qry, storage, toc
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
    return f'/api/editor/projects/{code}/toc'


def upload(client, code, content=b'# Contents', name='toc.md', **kwargs):
    return client.post(endpoint(code),
                       data={'file': (BytesIO(content), name)}, **kwargs)


def test_upload_read_and_project_isolation(client, books):
    first, second = books
    assert client.get(endpoint(first)).json == {'text': ''}
    text = '# Contents\n\n1. Introduction\n'
    response = upload(client, first, text.encode())
    assert response.status_code == 200
    assert response.json == {'text': text}
    assert client.get(endpoint(first)).json == {'text': text}
    assert client.get(endpoint(second)).json == {'text': ''}
    # It is stored as a markdown file in the project's folder.
    path = storage.project_directory(first) / 'table_of_contents.md'
    assert path.read_text(encoding='utf-8') == text


def test_uploading_again_replaces_it(client, books):
    upload(client, books[0], b'# Old')
    assert upload(client, books[0], b'# New', 'other.markdown'
                  ).status_code == 200
    assert client.get(endpoint(books[0])).json == {'text': '# New'}


def test_the_upload_name_does_not_choose_where_it_is_saved(client, books):
    response = upload(client, books[0], b'# Contents', '../../evil.md')
    assert response.status_code == 200
    path = storage.project_directory(books[0]) / 'table_of_contents.md'
    assert path.read_text(encoding='utf-8') == '# Contents'


@pytest.mark.parametrize('content,name', [
    (b'# Contents', 'toc.txt'), (b'# Contents', 'toc.docx'),
    (b'# Contents', 'toc'), (b'', 'toc.md'), (b'  \n', 'toc.md'),
    (b'\xff\xfe\x00bad', 'toc.md'),
    (b'a' * (toc.MAX_BYTES + 1), 'toc.md'),
])
def test_bad_uploads_are_400_and_change_nothing(client, books, content, name):
    upload(client, books[0], b'Keep me')
    assert upload(client, books[0], content, name).status_code == 400
    assert toc.read(books[0]) == 'Keep me'


def test_no_file_chosen_is_400(client, books):
    response = client.post(endpoint(books[0]), data={'other': 'x'},
                           content_type='multipart/form-data')
    assert response.status_code == 400


@pytest.mark.parametrize('payload', [
    {'text': 5}, {'text': None}, {'text': ['a']}, {'text': True},
    {'text': '# Typed in'}, {},
])
def test_typed_text_is_not_accepted_and_is_never_a_500(client, books,
                                                       payload):
    upload(client, books[0], b'Keep me')
    response = client.post(endpoint(books[0]), json=payload)
    assert response.status_code == 415
    assert toc.read(books[0]) == 'Keep me'


def test_editor_access_and_cross_origin(client, books):
    url = endpoint(books[0])
    assert client.get(url, headers={'Authorization': ''}).status_code == 401
    assert upload(client, books[0],
                  headers={'Authorization': ''}).status_code == 401
    assert upload(client, books[0],
                  headers={'Origin': 'https://other.example'}
                  ).status_code == 403
    assert toc.read(books[0]) == ''


def test_missing_and_wrong_type_of_project(client):
    assert client.get(endpoint('missing')).status_code == 404
    assert upload(client, 'missing').status_code == 404
    code = qry.add(qry.TEST_SAMPLE)
    try:
        assert client.get(endpoint(code)).status_code == 400
        assert upload(client, code).status_code == 400
    finally:
        qry.delete(code)


def test_storage_failure_is_reported(client, books, monkeypatch):
    def fail(*args):
        raise OSError('Disk full')

    monkeypatch.setattr(toc, '_write', fail)
    assert upload(client, books[0]).status_code == 500
    assert toc.read(books[0]) == ''
