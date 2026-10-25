"""Contributor storage and editor workflow tests."""
import json
import os
from base64 import b64encode
from io import BytesIO
from unittest.mock import patch

import pytest

from projects import query as projects_query
from server.projects import ContributorStore, ProjectContributorStore
from server.endpoints import app


@pytest.fixture
def contributor_store(tmp_path):
    return ContributorStore(tmp_path)


@pytest.fixture
def contributor(contributor_store):
    return contributor_store.add_contributor('Ada Writer')


def test_save_bio_persists_text_and_flag(contributor_store, contributor,
                                         tmp_path):
    text = 'Ada writes fiction.\nHer work appears in literary journals.'

    result = contributor_store.save_piece(contributor['id'], 'bio', text)

    assert result['Bio'] is True
    directory = tmp_path / contributor['id']
    assert (directory / 'bio.txt').read_text(encoding='utf-8') == text
    assert json.loads((directory / 'contributor.json').read_text())['Bio']
    assert ContributorStore(tmp_path).get_piece(
        contributor['id'], 'bio') == text
    assert contributor_store.list_contributors() == [result]


def test_submission_does_not_mark_bio_received(contributor_store, contributor):
    assert contributor_store.get_piece(contributor['id'], 'bio') == ''
    result = contributor_store.save_piece(
        contributor['id'], 'submission', 'A short story.')
    assert result['Submission'] is True
    assert result['Bio'] is False


@pytest.mark.parametrize('contributor_id', ['../outside', '/etc', 'missing'])
def test_rejects_unsafe_ids(contributor_store, contributor_id):
    with pytest.raises(ValueError):
        contributor_store.save_piece(contributor_id, 'bio', 'Text')


def test_unknown_contributor(contributor_store):
    with pytest.raises(KeyError):
        contributor_store.save_piece('a' * 32, 'bio', 'Text')


@pytest.mark.parametrize('name', ['', '  ', None, 42, 'a' * 201])
def test_invalid_contributor_name(contributor_store, name):
    with pytest.raises(ValueError):
        contributor_store.add_contributor(name)


@pytest.mark.parametrize('piece_type,text', [
    ('../bio', 'Text'), ('bio', ''), ('bio', '  '),
    ('bio', None), ('bio', 'a' * 100_001),
], ids=['invalid-type', 'empty', 'whitespace', 'non-string', 'too-long'])
def test_invalid_piece_does_not_change_record(contributor_store, contributor,
                                              piece_type, text):
    with pytest.raises(ValueError):
        contributor_store.save_piece(contributor['id'], piece_type, text)
    assert contributor_store.list_contributors() == [contributor]


@pytest.mark.parametrize('operation', ['get_piece', 'save_piece'])
def test_unknown_piece_type_raises_value_error(contributor_store, contributor,
                                               operation):
    with pytest.raises(ValueError, match='Unknown piece type'):
        if operation == 'get_piece':
            contributor_store.get_piece(contributor['id'], 'draft')
        else:
            contributor_store.save_piece(contributor['id'], 'draft', 'Text')


def test_failed_file_write_does_not_mark_bio(contributor_store, contributor):
    with patch.object(contributor_store, '_write',
                      side_effect=OSError('Disk full')):
        with pytest.raises(OSError):
            contributor_store.save_piece(contributor['id'], 'bio', 'Text')
    assert contributor_store.list_contributors()[0]['Bio'] is False


def test_replace_bio_preserves_unicode_and_other_contributors(
        contributor_store, contributor):
    other = contributor_store.add_contributor('Other Writer')
    contributor_store.save_piece(contributor['id'], 'bio', 'Original')
    text = 'Ren\u00e9e writes poetry.\n\nSecond paragraph.'
    contributor_store.save_piece(contributor['id'], 'bio', text)
    assert contributor_store.get_piece(contributor['id'], 'bio') == text
    assert contributor_store.get_piece(other['id'], 'bio') == ''


@patch('server.projects.contributors.require_volume', autospec=True)
@patch('server.projects.contributors.fetch_list', autospec=True)
def test_project_store_lists_contributors(mock_fetch, mock_require_volume):
    records = [{'id': 'a' * 32, 'name': 'Ada'}]
    mock_fetch.return_value = records

    result = ProjectContributorStore('b' * 32).list_contributors()

    assert result == records
    mock_require_volume.assert_called_once_with('b' * 32)
    mock_fetch.assert_called_once_with('b' * 32)


@patch('server.projects.contributors.require_volume', autospec=True)
@patch('server.projects.contributors.add', autospec=True)
def test_project_store_adds_contributor(mock_add, mock_require_volume):
    record = {'id': 'a' * 32, 'name': 'Ada'}
    mock_add.return_value = record

    result = ProjectContributorStore('b' * 32).add_contributor('Ada')

    assert result == record
    mock_require_volume.assert_called_once_with('b' * 32)
    mock_add.assert_called_once_with('b' * 32, 'Ada')


@patch('server.projects.contributors.require_volume', autospec=True)
@patch('server.projects.materials.read_text', autospec=True)
def test_project_store_reads_piece(mock_read, mock_require_volume):
    mock_read.return_value = 'Biography text'

    result = ProjectContributorStore('b' * 32).get_piece('a' * 32, 'bio')

    assert result == 'Biography text'
    mock_require_volume.assert_called_once_with('b' * 32)
    mock_read.assert_called_once_with('b' * 32, 'a' * 32, 'bio')


@patch('server.projects.contributors.require_volume', autospec=True)
@patch('server.projects.materials.save_text', autospec=True)
def test_project_store_saves_piece(mock_save, mock_require_volume):
    record = {'id': 'a' * 32, 'Bio': True}
    mock_save.return_value = record

    result = ProjectContributorStore('b' * 32).save_piece(
        'a' * 32, 'bio', 'Biography text')

    assert result == record
    mock_require_volume.assert_called_once_with('b' * 32)
    mock_save.assert_called_once_with(
        'b' * 32, 'a' * 32, 'bio', 'Biography text')


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


@pytest.mark.parametrize(('filename', 'data'), [
    ('bio.docx', b'PK\x03\x04word document'),
    ('bio.pdf', b'%PDF-1.7 document'),
])
def test_editor_uploads_documents(editor_client, tmp_path, filename, data):
    created = editor_client.post('/api/contributors', json={'name': 'Ada'})
    contributor = created.get_json()
    url = f"/api/contributors/{contributor['id']}/pieces/bio/document"

    response = editor_client.post(
        url, data={'file': (BytesIO(data), filename)},
        content_type='multipart/form-data')

    assert response.status_code == 200
    assert response.get_json()['Bio'] is True
    assert (tmp_path / contributor['id'] / filename).read_bytes() == data


def test_editor_upload_uses_project_material_store(editor_client):
    record = {'id': 'a' * 32, 'Bio': True}
    with patch('server.editor.ProjectContributorStore') as project_store:
        project_store.return_value.save_file.return_value = record
        response = editor_client.post(
            f"/api/contributors/{record['id']}/pieces/bio/document"
            '?project=book-code',
            data={'file': (BytesIO(b'%PDF-1.7 document'), 'bio.pdf')},
            content_type='multipart/form-data')

    assert response.status_code == 200
    project_store.assert_called_once_with('book-code')
    project_store.return_value.save_file.assert_called_once_with(
        record['id'], 'bio', b'%PDF-1.7 document', '.pdf')


@pytest.mark.parametrize('filename', ['bio.txt', 'bio.exe', ''])
def test_editor_rejects_unsupported_or_missing_document(editor_client,
                                                         filename):
    created = editor_client.post('/api/contributors', json={'name': 'Ada'})
    url = f"/api/contributors/{created.get_json()['id']}/pieces/bio/document"
    data = {'file': (BytesIO(b'data'), filename)} if filename else {}

    response = editor_client.post(url, data=data,
                                  content_type='multipart/form-data')

    assert response.status_code == 400


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


@pytest.fixture
def edited_books():
    from projects import contributors, query
    from backendcore.data.caching import get_cache

    codes = [query.add({**query.TEST_SAMPLE, query.TYPE: query.COLLECTION,
                        query.NAME: name}) for name in ('Book A', 'Book B')]
    yield codes
    for code in codes:
        for person in contributors.fetch_list(code):
            get_cache(contributors.COLLECT).delete(person['id'])
        query.delete(code)


@pytest.mark.skipif(
    os.getenv('RUN_BACKEND_INTEGRATION_TESTS') != '1',
    reason='Requires the configured BackEndCore/MongoDB database.',
)
def test_editor_project_selection_and_isolation(editor_client, edited_books):
    from projects.storage import project_directory

    first, second = edited_books
    response = editor_client.get('/api/editor/projects')
    assert response.status_code == 200
    assert {first, second} <= {p['code'] for p in response.json['projects']}
    created = editor_client.post('/api/contributors',
                                 query_string={'project': first},
                                 json={'name': 'Ada'})
    assert created.status_code == 201
    person = created.json
    url = f"/api/contributors/{person['id']}/pieces/bio"
    saved = editor_client.post(url, query_string={'project': first},
                               json={'text': 'Book A biography'})
    assert saved.status_code == 200
    assert saved.json['Bio'] is True
    path = project_directory(first) / 'bios' / f"{person['id']}.txt"
    assert path.read_text() == 'Book A biography'
    assert editor_client.get(url, query_string={'project': first}).json == {
        'text': 'Book A biography'}
    response = editor_client.get(url, query_string={'project': second})
    assert response.status_code == 404
    assert editor_client.post(url, query_string={'project': second},
                              json={'text': 'Wrong book'}).status_code == 404
    assert editor_client.get('/api/contributors',
                             query_string={'project': second}).json == {
        'contributors': []}
    # The existing unassigned editor still uses its original files.
    assert editor_client.get('/api/contributors').json == {'contributors': []}
    assert b'id="project-select"' in editor_client.get('/editor').data


@patch('server.editor.ProjectContributorStore', autospec=True)
def test_project_query_uses_project_contributor_store(
        mock_project_store, editor_client):
    records = [{'id': 'a' * 32, 'name': 'Ada'}]
    mock_project_store.return_value.list_contributors.return_value = records

    response = editor_client.get(
        '/api/contributors', query_string={'project': 'b' * 32})

    assert response.status_code == 200
    assert response.json == {'contributors': records}
    mock_project_store.assert_called_once_with('b' * 32)
    mock_project_store.return_value.list_contributors.assert_called_once_with()


@patch('server.editor.ProjectContributorStore', autospec=True)
def test_project_list_filters_and_sorts_edited_volumes(
        mock_project_store, editor_client):
    mock_project_store.side_effect = AssertionError(
        'Listing volumes should not create a contributor store.')
    projects = [
        {projects_query.CODE: 'a', projects_query.NAME: 'zeta',
         projects_query.TYPE: projects_query.COLLECTION},
        {projects_query.CODE: 'b', projects_query.NAME: 'Essay',
         projects_query.TYPE: projects_query.ESSAY},
        {projects_query.CODE: 'c', projects_query.NAME: 'Alpha',
         projects_query.TYPE: projects_query.COLLECTION},
    ]

    with patch('server.editor.projects_query.fetch_list',
               autospec=True, return_value=projects) as mock_fetch:
        response = editor_client.get('/api/editor/projects')

    assert response.status_code == 200
    assert [project[projects_query.CODE]
            for project in response.json['projects']] == ['c', 'a']
    mock_fetch.assert_called_once_with()
    mock_project_store.assert_not_called()


@patch('server.editor.ProjectContributorStore', autospec=True,
       side_effect=KeyError('Project not found.'))
def test_unknown_project_does_not_fall_back_to_legacy(
        mock_project_store, editor_client):
    response = editor_client.post('/api/contributors?project=missing',
                                  json={'name': 'Ada'})
    assert response.status_code == 404
    mock_project_store.assert_called_once_with('missing')
    assert editor_client.get('/api/contributors').json == {'contributors': []}


def test_project_list_requires_editor_auth(editor_client):
    assert editor_client.get('/api/editor/projects',
                             headers={'Authorization': ''}).status_code == 401
