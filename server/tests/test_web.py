"""Tests for the projects web interface (issue #4)."""
from base64 import b64encode
from io import BytesIO
from uuid import uuid4
from unittest.mock import Mock

import pytest

from projects import materials, toc
import projects.person_project as pp
import projects.people as people
import projects.query as pqry
from server.endpoints import app

USERNAME = 'editor'
PASSWORD = 'test-password'


@pytest.mark.parametrize('prompt', [False, True])
def test_command_line_startup(monkeypatch, tmp_path, prompt):
    from server import __main__ as cli

    for name in ('DATABASE', 'OUR_NAME', 'WRITERS_EDITOR_USERNAME',
                 'WRITERS_EDITOR_PASSWORD', 'PORT'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('SQLITE_LOC', str(tmp_path / 'database'))
    if not prompt:
        monkeypatch.setenv('WRITERS_EDITOR_PASSWORD', PASSWORD)
    password_prompt = Mock(return_value=PASSWORD)
    run = Mock()
    monkeypatch.setattr(cli, 'getpass', password_prompt)
    monkeypatch.setattr(app, 'run', run)
    monkeypatch.setitem(app.config, 'EDITOR_USERNAME', USERNAME)
    monkeypatch.setitem(app.config, 'EDITOR_PASSWORD', PASSWORD)

    cli.main(['--host', '127.0.0.1', '--port', '8123'] if prompt else [])

    run.assert_called_once_with(host='127.0.0.1',
                                port=8123 if prompt else 8002)
    assert cli.os.environ['DATABASE'] == 'sqlite'
    assert (tmp_path / 'database').is_dir()
    assert app.config['EDITOR_PASSWORD'] == PASSWORD
    assert app.config['EDITOR_USERNAME'] == USERNAME
    if prompt:
        password_prompt.assert_called_once()
    else:
        password_prompt.assert_not_called()


def test_command_line_rejects_empty_password(monkeypatch):
    from server import __main__ as cli

    monkeypatch.delenv('WRITERS_EDITOR_PASSWORD', raising=False)
    monkeypatch.setattr(cli, 'getpass', Mock(return_value='  '))
    with pytest.raises(SystemExit) as error:
        cli.main([])
    assert error.value.code == 2


@pytest.mark.parametrize('port', ['0', '65536', 'not-a-port'])
def test_command_line_rejects_invalid_port(port):
    from server import __main__ as cli

    with pytest.raises(SystemExit) as error:
        cli.main(['--port', port])
    assert error.value.code == 2


def _login_header(username=USERNAME, password=PASSWORD):
    """Build the header a browser sends after the login popup."""
    token = b64encode(f'{username}:{password}'.encode()).decode()
    return {'Authorization': f'Basic {token}'}


@pytest.fixture
def client():
    """A fake browser that talks to the app without starting a server."""
    app.config.update(TESTING=True, EDITOR_USERNAME=USERNAME,
                      EDITOR_PASSWORD=PASSWORD)
    with app.test_client() as test_client:
        yield test_client


def _codes_named(name):
    """Find the codes of every project with this name."""
    return [proj[pqry.CODE] for proj in pqry.fetch_list()
            if proj[pqry.NAME] == name]


def test_home_needs_login(client):
    response = client.get('/web/')
    assert response.status_code == 401
    assert 'WWW-Authenticate' in response.headers


def test_wrong_password_rejected(client):
    response = client.get('/web/', headers=_login_header(password='nope'))
    assert response.status_code == 401


def test_locked_when_no_password_configured(client):
    app.config['EDITOR_PASSWORD'] = None
    response = client.get('/web/', headers=_login_header())
    assert response.status_code == 503


def test_home_page_loads(client):
    response = client.get('/web/', headers=_login_header())
    assert response.status_code == 200
    assert b'Projects' in response.data
    assert response.headers['Cache-Control'] == 'no-store'


def test_create_list_edit_delete(client):
    name = 'Web Test Volume'
    # Create.
    response = client.post('/web/projects', headers=_login_header(),
                           data={'name': name, 'type': pqry.COLLECTION},
                           follow_redirects=True)
    assert response.status_code == 200
    assert name.encode() in response.data
    codes = _codes_named(name)
    assert len(codes) == 1
    code = codes[0]
    assert pqry.fetch_by_key(code)[pqry.USER] == USERNAME

    # Edit page shows the current name.
    response = client.get(f'/web/projects/{code}/edit',
                          headers=_login_header())
    assert name.encode() in response.data

    assert b'name="type"' not in response.data
    assert b'Edited volume (multi-author)' in response.data

    # A crafted request must not change the type, name, or author list.
    response = client.post(f'/web/projects/{code}/edit',
                           headers=_login_header(), follow_redirects=True,
                           data={'name': 'Unexpected rename',
                                 'type': pqry.ESSAY, 'authors': 'Someone'})
    assert b'type cannot change' in response.data
    assert pqry.fetch_by_key(code)[pqry.NAME] == name
    assert not pp.fetch_authors(code)

    new_name = 'Renamed Volume'
    client.post(f'/web/projects/{code}/edit', headers=_login_header(),
                data={'name': new_name})
    project = pqry.fetch_by_key(code)
    assert project[pqry.NAME] == new_name
    assert project[pqry.TYPE] == pqry.COLLECTION

    # Delete.
    client.post(f'/web/projects/{code}/delete', headers=_login_header())
    assert pqry.fetch_by_key(code) is None


def test_blank_name_shows_error(client):
    response = client.post('/web/projects', headers=_login_header(),
                           data={'name': '   ', 'type': pqry.ESSAY},
                           follow_redirects=True)
    assert b'non-empty' in response.data


def test_bad_type_shows_error(client):
    response = client.post('/web/projects', headers=_login_header(),
                           data={'name': 'Bad Type', 'type': 'novel'},
                           follow_redirects=True)
    assert b'Invalid project type' in response.data
    assert _codes_named('Bad Type') == []


def test_missing_project_redirects(client):
    response = client.get('/web/projects/doesnotexist/edit',
                          headers=_login_header(), follow_redirects=True)
    assert b'no longer exists' in response.data


def test_cross_site_post_blocked(client):
    headers = _login_header()
    headers['Origin'] = 'https://evil.example'
    response = client.post('/web/projects', headers=headers,
                           data={'name': 'Sneaky', 'type': pqry.ESSAY})
    assert response.status_code == 403
    assert _codes_named('Sneaky') == []


def test_same_origin_label_allowed_behind_proxy(client):
    # In Codespaces the browser's address differs from the server's,
    # but the browser still labels the form as same-origin.
    headers = _login_header()
    headers['Origin'] = 'https://studious-robot-8002.app.github.dev'
    headers['Sec-Fetch-Site'] = 'same-origin'
    response = client.post('/web/projects', headers=headers,
                           data={'name': 'Proxy Book', 'type': pqry.ESSAY})
    assert response.status_code == 302
    codes = _codes_named('Proxy Book')
    assert len(codes) == 1
    pqry.delete(codes[0])


def test_cross_site_label_blocked(client):
    headers = _login_header()
    headers['Sec-Fetch-Site'] = 'cross-site'
    response = client.post('/web/projects', headers=headers,
                           data={'name': 'Sneaky Two', 'type': pqry.ESSAY})
    assert response.status_code == 403
    assert _codes_named('Sneaky Two') == []


def test_create_journal_issue(client):
    response = client.post('/web/projects', headers=_login_header(),
                           data={'name': 'Spring Issue',
                                 'type': pqry.JOURNAL_ISSUE},
                           follow_redirects=True)
    assert b'Journal Issue' in response.data
    codes = _codes_named('Spring Issue')
    assert len(codes) == 1
    assert pqry.fetch_by_key(codes[0])[pqry.TYPE] == pqry.JOURNAL_ISSUE
    pqry.delete(codes[0])

    
def _delete_authors(names):
    for name in names:
        for author_id in people.fetch_by_name(name):
            people.delete(author_id)


@pytest.fixture
def project_code():
    code = pqry.add(dict(pqry.TEST_SAMPLE))
    yield code
    if pqry.is_valid(code):
        pqry.delete(code)


def _edit_form(code, author_text):
    project = pqry.fetch_by_key(code)
    return {'name': project[pqry.NAME], 'type': project[pqry.TYPE],
            'authors': author_text}


def test_edit_saves_author_list(client, project_code):
    zed, ada = f'Zed {uuid4().hex[:8]}', f'Ada {uuid4().hex[:8]}'
    try:
        # Blank lines and extra spaces are ignored.
        client.post(f'/web/projects/{project_code}/edit',
                    headers=_login_header(),
                    data=_edit_form(project_code, f'  {zed}\n\n{ada}\n'))
        found = [author[people.NAME]
                 for author in pp.fetch_authors(project_code)]
        assert found == [ada, zed]

        # The edit page shows the saved authors, one per line.
        response = client.get(f'/web/projects/{project_code}/edit',
                              headers=_login_header())
        assert f'{ada}\n{zed}'.encode() in response.data
    finally:
        _delete_authors([zed, ada])


def test_edit_replaces_author_list(client, project_code):
    keep, drop = f'Keep {uuid4().hex[:8]}', f'Drop {uuid4().hex[:8]}'
    try:
        pp.set_authors(project_code, [keep, drop])
        client.post(f'/web/projects/{project_code}/edit',
                    headers=_login_header(),
                    data=_edit_form(project_code, keep))
        found = [author[people.NAME]
                 for author in pp.fetch_authors(project_code)]
        assert found == [keep]
    finally:
        _delete_authors([keep, drop])


def test_edit_bad_author_saves_nothing(client, project_code):
    old_name = pqry.fetch_by_key(project_code)[pqry.NAME]
    data = _edit_form(project_code, 'x' * (people.MAX_NAME_LEN + 1))
    data['name'] = 'Should Not Save'
    response = client.post(f'/web/projects/{project_code}/edit',
                           headers=_login_header(), data=data,
                           follow_redirects=True)
    assert b'Person name must be' in response.data
    assert pqry.fetch_by_key(project_code)[pqry.NAME] == old_name
    assert pp.fetch_authors(project_code) == []


def test_create_goes_to_authors(client):
    name = f'Next Step {uuid4().hex[:8]}'
    response = client.post('/web/projects', headers=_login_header(),
                           data={'name': name, 'type': pqry.ESSAY})
    code = _codes_named(name)[0]
    try:
        # After creating, the next step is adding authors.
        assert response.headers['Location'].endswith(
            f'/web/projects/{code}/edit#authors')
    finally:
        pqry.delete(code)


def test_list_shows_authors(client, project_code):
    name = f'Shown {uuid4().hex[:8]}'
    response = client.get('/web/projects', headers=_login_header())
    assert b'No authors yet.' in response.data
    try:
        pp.set_authors(project_code, [name])
        response = client.get('/web/projects', headers=_login_header())
        assert f'<li>{name}</li>'.encode() in response.data
    finally:
        _delete_authors([name])




def _new_project(name, proj_type):
    """Create a project directly and give back its code."""
    return pqry.add({pqry.NAME: name, pqry.TYPE: proj_type,
                     pqry.USER: USERNAME})


@pytest.mark.parametrize('proj_type', [pqry.COLLECTION, pqry.JOURNAL_ISSUE])
def test_contributors_page_for_multi_author_projects(client, proj_type):
    code = _new_project('Contributor Book', proj_type)
    try:
        # The projects list links to the project's Contributors page.
        listing = client.get('/web/projects', headers=_login_header())
        url = f'/web/projects/{code}/contributors'
        assert url.encode() in listing.data
        page = client.get(url, headers=_login_header())
        assert page.status_code == 200
        assert b'Contributor Book' in page.data
        assert f'data-project="{code}"'.encode() in page.data
    finally:
        pqry.delete(code)


def test_no_contributors_page_for_solo_book(client):
    code = _new_project('Just Me', pqry.SOLO_BOOK)
    try:
        url = f'/web/projects/{code}/contributors'
        listing = client.get('/web/projects', headers=_login_header())
        assert url.encode() not in listing.data
        page = client.get(url, headers=_login_header(),
                          follow_redirects=True)
        assert b'Only edited volumes and journal issues' in page.data
    finally:
        pqry.delete(code)


def test_contributors_page_missing_project(client):
    page = client.get('/web/projects/doesnotexist/contributors',
                      headers=_login_header(), follow_redirects=True)
    assert b'no longer exists' in page.data
@pytest.mark.parametrize('proj_type', pqry.MULTI_AUTHOR_TYPES)
def test_create_volume_with_selected_components(client, proj_type):
    from projects.storage import project_directory
    headers = _login_header()
    form = client.get('/web/projects', headers=headers)
    for field in pqry.REQUIREMENT_FIELDS:
        assert f'name="{field}"'.encode() in form.data
    name = 'Volume with abstracts and keywords'
    client.post('/web/projects', headers=headers, data={
        'name': name, 'type': proj_type,
        'requires_abstract': 'on', 'requires_keywords': 'on'})
    code, = _codes_named(name)
    try:
        project = pqry.fetch_by_key(code)
        assert project['requires_abstract'] and project['requires_keywords']
        assert not project['requires_bio']
        folders = {p.name for p in project_directory(code).iterdir()}
        assert folders == {'chapters', 'drafts', 'Proposal',
                           'abstracts', 'keywords'}
    finally:
        pqry.delete(code)


# --- Screens for filling in the table of contents and authors' pieces

@pytest.fixture(params=pqry.MULTI_AUTHOR_TYPES)
def volume(request):
    """A multi-author project with two authors, cleaned up afterwards."""
    code = pqry.add({**pqry.TEST_SAMPLE, pqry.TYPE: request.param})
    names = [f'Fill {uuid4().hex[:8]}', f'Other {uuid4().hex[:8]}']
    pp.set_authors(code, names)
    ids = {author[people.NAME]: author[people.ID]
           for author in pp.fetch_authors(code)}
    yield code, names, ids
    _delete_authors(names)
    if pqry.is_valid(code):
        pqry.delete(code)


def _materials_url(code):
    return f'/web/projects/{code}/materials'


def _toc_url(code):
    return f'/web/projects/{code}/toc'


def _piece_url(code, person_id, piece):
    return f'/web/projects/{code}/authors/{person_id}/{piece}'


def test_materials_page_lists_authors_as_pending(client, volume):
    code, names, _ = volume
    response = client.get(_materials_url(code), headers=_login_header())
    assert response.status_code == 200
    for name in names:
        assert name.encode() in response.data
    assert b'Biography' in response.data
    assert b'Pending' in response.data
    assert b'Received' not in response.data


def _toc_upload(content, name='toc.md'):
    return {'file': (BytesIO(content), name)}


def test_toc_is_shared_with_the_contributor_editor(client, volume):
    code, _, _ = volume
    response = client.post(_toc_url(code), headers=_login_header(),
                           data=_toc_upload(b'# Contents\r\n\r\n1. Intro'),
                           content_type='multipart/form-data',
                           follow_redirects=True)
    assert response.status_code == 200
    assert b'Saved the table of contents' in response.data
    expected = '# Contents\n\n1. Intro'
    assert toc.read(code) == expected
    # It is a markdown file in the project folder, not a project field.
    assert 'toc' not in pqry.fetch_by_key(code)
    editor_view = client.get(f'/api/editor/projects/{code}/toc',
                             headers=_login_header())
    assert editor_view.json == {'text': expected}
    page = client.get(_materials_url(code), headers=_login_header())
    assert b'1. Intro' in page.data


def test_toc_bad_uploads_are_rejected(client, volume):
    code, _, _ = volume
    client.post(_toc_url(code), headers=_login_header(),
                data=_toc_upload(b'Keep'), content_type='multipart/form-data')
    bad = [(b'a' * 100_001, 'big.md', b'at most 100,000 characters'),
           (b'text', 'notes.txt', b'Choose a .md'),
           (b'', 'empty.md', b'not empty'),
           (b'\xff\xfe\x00bad', 'bad.md', b'UTF-8')]
    for content, name, message in bad:
        response = client.post(_toc_url(code), headers=_login_header(),
                               data=_toc_upload(content, name),
                               content_type='multipart/form-data',
                               follow_redirects=True)
        assert message in response.data
        assert toc.read(code) == 'Keep'
    # No file at all, and a plain form field instead of a file.
    for data in ({}, {'toc': 'typed text'}):
        response = client.post(_toc_url(code), headers=_login_header(),
                               data=data, follow_redirects=True)
        assert b'Choose a markdown' in response.data
        assert toc.read(code) == 'Keep'


def test_editor_toc_upload_never_returns_500(client, volume):
    code, _, _ = volume
    url = f'/api/editor/projects/{code}/toc'
    headers = _login_header()
    # JSON bodies, including a non-string "text", are refused cleanly.
    for body in ({'text': 5}, {'text': ['a']}, {'text': None}):
        response = client.post(url, headers=headers, json=body)
        assert response.status_code == 415
    response = client.post(url, headers=headers,
                           data=_toc_upload(b'# Editor upload'),
                           content_type='multipart/form-data')
    assert response.status_code == 200
    assert toc.read(code) == '# Editor upload'
    response = client.post(url, headers=headers,
                           data=_toc_upload(b'x', 'x.exe'),
                           content_type='multipart/form-data')
    assert response.status_code == 400


def test_fill_in_and_edit_a_piece(client, volume):
    code, names, ids = volume
    person = ids[names[0]]
    url = _piece_url(code, person, 'bio')
    assert client.get(url, headers=_login_header()).status_code == 200
    # Only saving marks the piece received, not just looking.
    assert pp.fetch_author_status(code, person)['Bio'] is False

    response = client.post(url, headers=_login_header(),
                           data={'text': 'Ada writes.\r\nSecond line.'},
                           follow_redirects=True)
    assert b'Saved biography' in response.data
    assert pp.fetch_author_status(code, person)['Bio'] is True
    assert (materials.read_text(code, person, 'bio')
            == 'Ada writes.\nSecond line.')
    assert b'Ada writes.' in client.get(url, headers=_login_header()).data

    # Saving again replaces the text.
    client.post(url, headers=_login_header(), data={'text': 'New bio'})
    assert materials.read_text(code, person, 'bio') == 'New bio'
    overview = client.get(_materials_url(code), headers=_login_header())
    assert b'Received' in overview.data


def test_authors_have_separate_materials(client, volume):
    code, names, ids = volume
    texts = ['First address', 'Second address']
    for name, text in zip(names, texts):
        client.post(_piece_url(code, ids[name], 'address'),
                    headers=_login_header(), data={'text': text})
    for name, text in zip(names, texts):
        assert materials.read_text(code, ids[name], 'address') == text


def test_blank_text_is_rejected(client, volume):
    code, names, ids = volume
    person = ids[names[0]]
    response = client.post(_piece_url(code, person, 'bio'),
                           headers=_login_header(), data={'text': '   '})
    assert response.status_code == 400
    assert b'Enter some text' in response.data
    assert pp.fetch_author_status(code, person)['Bio'] is False


def test_storage_failure_keeps_what_was_typed(client, volume, monkeypatch):
    code, names, ids = volume

    def fail(*args):
        raise OSError('Disk full')

    monkeypatch.setattr(materials, '_write', fail)
    response = client.post(_piece_url(code, ids[names[0]], 'bio'),
                           headers=_login_header(),
                           data={'text': 'Typed bio'})
    assert response.status_code == 500
    assert b'Could not save' in response.data
    assert b'Typed bio' in response.data


def test_unknown_piece_and_non_author(client, volume):
    code, names, ids = volume
    response = client.get(_piece_url(code, ids[names[0]], 'nonsense'),
                          headers=_login_header())
    assert response.status_code == 404
    response = client.get(_piece_url(code, 'f' * 32, 'bio'),
                          headers=_login_header(), follow_redirects=True)
    assert b'not an author' in response.data


def test_materials_only_for_edited_volumes(client, project_code):
    response = client.get(_materials_url(project_code),
                          headers=_login_header(), follow_redirects=True)
    assert b'only for edited volumes' in response.data


def test_materials_for_missing_project(client):
    response = client.get(_materials_url('doesnotexist'),
                          headers=_login_header(), follow_redirects=True)
    assert b'no longer exists' in response.data


def test_materials_need_login_and_same_site_posts(client, volume):
    code, names, ids = volume
    assert client.get(_materials_url(code)).status_code == 401
    headers = _login_header()
    headers['Sec-Fetch-Site'] = 'cross-site'
    response = client.post(_toc_url(code), headers=headers,
                           data=_toc_upload(b'Sneaky'),
                           content_type='multipart/form-data')
    assert response.status_code == 403
    assert toc.read(code) == ''
    response = client.post(_piece_url(code, ids[names[0]], 'bio'),
                           headers=headers, data={'text': 'Sneaky'})
    assert response.status_code == 403
    assert pp.fetch_author_status(code, ids[names[0]])['Bio'] is False


def test_list_links_to_materials_for_volumes_only(client, volume,
                                                  project_code):
    code, _, _ = volume
    response = client.get('/web/projects', headers=_login_header())
    assert _materials_url(code).encode() in response.data
    assert _materials_url(project_code).encode() not in response.data


def test_edit_links_to_materials_for_multi_author_projects(client, volume):
    code, _, _ = volume
    response = client.get(f'/web/projects/{code}/edit', headers=_login_header())
    assert _materials_url(code).encode() in response.data
