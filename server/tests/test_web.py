"""Tests for the projects web interface (issue #4)."""
from base64 import b64encode
from uuid import uuid4
from unittest.mock import Mock

import pytest

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

    # Rename and change type.
    new_name = 'Web Test Essay'
    client.post(f'/web/projects/{code}/edit', headers=_login_header(),
                data={'name': new_name, 'type': pqry.ESSAY})
    project = pqry.fetch_by_key(code)
    assert project[pqry.NAME] == new_name
    assert project[pqry.TYPE] == pqry.ESSAY

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
