"""Contributor storage and editor workflow tests."""
import json
from base64 import b64encode
from unittest.mock import patch

import pytest

from server.projects import ContributorStore
from server.endpoints import app


def test_save_bio_persists_text_and_flag(tmp_path):
    store = ContributorStore(tmp_path)
    contributor = store.add_contributor('Ada Writer')
    text = 'Ada writes fiction.\nHer work appears in literary journals.'

    result = store.save_piece(contributor['id'], 'bio', text)

    assert result['Bio'] is True
    directory = tmp_path / contributor['id']
    assert (directory / 'bio.txt').read_text(encoding='utf-8') == text
    assert json.loads((directory / 'contributor.json').read_text())['Bio']
    assert ContributorStore(tmp_path).get_piece(
        contributor['id'], 'bio') == text
    assert store.list_contributors() == [result]


def test_submission_does_not_mark_bio_received(tmp_path):
    store = ContributorStore(tmp_path)
    contributor = store.add_contributor('Ada Writer')
    assert store.get_piece(contributor['id'], 'bio') == ''
    result = store.save_piece(
        contributor['id'], 'submission', 'A short story.')
    assert result['Submission'] is True
    assert result['Bio'] is False


@pytest.mark.parametrize('contributor_id', ['../outside', '/etc', 'missing'])
def test_rejects_unsafe_ids(tmp_path, contributor_id):
    with pytest.raises(ValueError):
        ContributorStore(tmp_path).save_piece(contributor_id, 'bio', 'Text')


def test_unknown_contributor(tmp_path):
    with pytest.raises(KeyError):
        ContributorStore(tmp_path).save_piece('a' * 32, 'bio', 'Text')


@pytest.mark.parametrize('name', ['', '  ', None, 42, 'a' * 201])
def test_invalid_contributor_name(tmp_path, name):
    with pytest.raises(ValueError):
        ContributorStore(tmp_path).add_contributor(name)


@pytest.mark.parametrize('piece_type,text', [
    ('../bio', 'Text'), ('bio', ''), ('bio', '  '),
    ('bio', None), ('bio', 'a' * 100_001),
])
def test_invalid_piece_does_not_change_record(tmp_path, piece_type, text):
    store = ContributorStore(tmp_path)
    contributor = store.add_contributor('Ada Writer')
    with pytest.raises(ValueError):
        store.save_piece(contributor['id'], piece_type, text)
    assert store.list_contributors() == [contributor]


def test_failed_file_write_does_not_mark_bio(tmp_path):
    store = ContributorStore(tmp_path)
    contributor = store.add_contributor('Ada Writer')
    with patch.object(store, '_write', side_effect=OSError('Disk full')):
        with pytest.raises(OSError):
            store.save_piece(contributor['id'], 'bio', 'Text')
    assert store.list_contributors()[0]['Bio'] is False


def test_replace_bio_preserves_unicode_and_other_contributors(tmp_path):
    store = ContributorStore(tmp_path)
    contributor = store.add_contributor('Ada Writer')
    other = store.add_contributor('Other Writer')
    store.save_piece(contributor['id'], 'bio', 'Original')
    text = 'Ren\u00e9e writes poetry.\n\nSecond paragraph.'
    store.save_piece(contributor['id'], 'bio', text)
    assert store.get_piece(contributor['id'], 'bio') == text
    assert store.get_piece(other['id'], 'bio') == ''


@pytest.fixture
def editor_client(tmp_path, monkeypatch):
    monkeypatch.setitem(app.config, 'CONTRIBUTOR_DATA_DIR', tmp_path)
    monkeypatch.setitem(app.config, 'EDITOR_USERNAME', 'editor')
    monkeypatch.setitem(app.config, 'EDITOR_PASSWORD', 'test-editor-password')
    client = app.test_client()
    token = b64encode(b'editor:test-editor-password').decode()
    client.environ_base['HTTP_AUTHORIZATION'] = f'Basic {token}'
    return client


def test_editor_api_saves_bio(editor_client, tmp_path):
    created = editor_client.post('/api/contributors', json={'name': 'Ada'})
    assert created.status_code == 201
    contributor = created.get_json()
    url = f"/api/contributors/{contributor['id']}/pieces/bio"
    response = editor_client.post(url, json={'text': 'Author biography.'})
    assert response.status_code == 200
    assert response.get_json()['Bio'] is True
    assert editor_client.get(url).get_json()['text'] == 'Author biography.'
    records = editor_client.get('/api/contributors').get_json()['contributors']
    assert records == [response.get_json()]
    assert (tmp_path / contributor['id'] / 'bio.txt').exists()


@pytest.mark.parametrize('url', ['/editor', '/api/contributors'])
def test_editor_requires_authentication(editor_client, url):
    response = editor_client.get(url, headers={'Authorization': ''})
    assert response.status_code == 401
    assert 'Basic' in response.headers['WWW-Authenticate']
    assert response.headers['Cache-Control'] == 'no-store'


def test_editor_disabled_without_password(editor_client, monkeypatch):
    monkeypatch.setitem(app.config, 'EDITOR_PASSWORD', None)
    assert editor_client.get('/editor').status_code == 503


def test_wrong_editor_password_cannot_write(editor_client):
    token = b64encode(b'editor:wrong').decode()
    response = editor_client.post('/api/contributors', json={'name': 'Ada'},
                                  headers={'Authorization': f'Basic {token}'})
    assert response.status_code == 401


def test_cross_origin_write_rejected(editor_client):
    response = editor_client.post('/api/contributors', json={'name': 'Ada'},
                                  headers={'Origin': 'https://other.test'})
    assert response.status_code == 403


@pytest.mark.parametrize('payload', [None, [], 'Ada', {'name': ''}])
def test_api_rejects_invalid_payload(editor_client, payload):
    response = editor_client.post(
        '/api/contributors', data=json.dumps(payload),
        content_type='application/json')
    assert response.status_code == 400


def test_api_missing_contributor(editor_client):
    response = editor_client.post(
        f"/api/contributors/{'a' * 32}/pieces/bio", json={'text': 'Bio'})
    assert response.status_code == 404


def test_api_storage_failure(editor_client):
    with patch('server.editor.ContributorStore.add_contributor',
               side_effect=OSError('Disk full')):
        response = editor_client.post(
            '/api/contributors', json={'name': 'Ada'})
    assert response.status_code == 500
    assert 'Disk full' not in response.get_json()['error']


def test_endpoint_listing_still_works_with_editor_routes(editor_client):
    response = editor_client.get('/Endpoints/read')
    assert response.status_code == 200
    assert '/editor' in response.get_json()['Available endpoints']


def test_editor_page_and_assets(editor_client):
    response = editor_client.get('/editor')
    assert response.status_code == 200
    assert b'Writer\'s Workbench' in response.data
    assert b'id="piece-text"' in response.data
    assert editor_client.get('/static/editor.js').status_code == 200
    assert editor_client.get('/static/editor.css').status_code == 200
