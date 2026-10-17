"""Tests for the projects web interface (issue #4)."""
from base64 import b64encode

import pytest

import projects.query as pqry
from server.endpoints import app

USERNAME = 'editor'
PASSWORD = 'test-password'


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
