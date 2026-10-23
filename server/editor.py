"""Authenticated contributor editor and JSON endpoints."""
from secrets import compare_digest

from flask import Blueprint, current_app, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from server.projects import ContributorStore, ProjectContributorStore
from projects import query as projects_query


editor = Blueprint('editor', __name__, template_folder='templates')


def _store():
    project_code = request.args.get('project')
    if project_code:
        return ProjectContributorStore(project_code)
    return ContributorStore(current_app.config['CONTRIBUTOR_DATA_DIR'])


@editor.before_request
def require_editor():
    """Fail closed when editor credentials have not been configured."""
    password = current_app.config.get('EDITOR_PASSWORD')
    if not password:
        return jsonify(error='Editor access is not configured.'), 503
    auth = request.authorization
    username = current_app.config['EDITOR_USERNAME']
    if (auth is None or auth.type != 'basic'
            or not compare_digest((auth.username or '').encode(),
                                  username.encode())
            or not compare_digest((auth.password or '').encode(),
                                  password.encode())):
        return (jsonify(error='Editor authentication required.'), 401,
                {'WWW-Authenticate': 'Basic realm="Contributor editor", '
                                     'charset="UTF-8"'})
    if request.method == 'POST':
        origin = request.headers.get('Origin')
        if origin and origin != request.host_url.rstrip('/'):
            return jsonify(error='Cross-origin writes are not allowed.'), 403
        if request.content_length and request.content_length > 2_000_000:
            return jsonify(error='Request is too large.'), 413
        if not request.is_json:
            return jsonify(error='Send a JSON object.'), 415
    return None


@editor.after_request
def private_response(response):
    """Do not cache private contributor text or credentials."""
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response


def _payload():
    data = request.get_json()
    if not isinstance(data, dict):
        raise ValueError('Send a JSON object.')
    return data


@editor.errorhandler(ValueError)
def invalid_input(error):
    """Return validation errors without exposing server paths."""
    return jsonify(error=str(error)), 400


@editor.errorhandler(KeyError)
def missing_contributor(_error):
    """Report unknown contributors."""
    return jsonify(error='Project or contributor not found.'), 404


@editor.errorhandler(OSError)
def storage_failure(error):
    """Leave the draft available in the browser after a storage failure."""
    current_app.logger.error('Contributor storage failed: %s', error)
    return jsonify(error='Could not save contributor data. Try again.'), 500


@editor.errorhandler(HTTPException)
def request_failure(error):
    """Keep malformed request responses in the JSON API format."""
    return jsonify(error=error.description), error.code


@editor.get('/editor')
def editor_page():
    """Display the contributor workbench."""
    return render_template('editor.html')


@editor.get('/api/contributors')
def contributors():
    """List contributors and their received-piece flags."""
    return jsonify(contributors=_store().list_contributors())


@editor.post('/api/contributors')
def add_contributor():
    """Create a contributor record."""
    return jsonify(_store().add_contributor(_payload().get('name'))), 201


@editor.get('/api/contributors/<contributor_id>/pieces/<piece_type>')
def read_piece(contributor_id, piece_type):
    """Load a contributor's existing piece for editing."""
    return jsonify(text=_store().get_piece(contributor_id, piece_type))


@editor.post('/api/contributors/<contributor_id>/pieces/<piece_type>')
def save_piece(contributor_id, piece_type):
    """Save the piece and return updated contributor flags."""
    record = _store().save_piece(contributor_id, piece_type,
                                 _payload().get('text'))
    return jsonify(record)


@editor.get('/api/editor/projects')
def edited_volumes():
    """List edited volumes for the existing shared editor account."""
    volumes = [project for project in projects_query.fetch_list()
               if project[projects_query.TYPE] == projects_query.COLLECTION]
    volumes.sort(key=lambda project: project[projects_query.NAME].casefold())
    return jsonify(projects=volumes)


def _volume_requirements(code):
    project = projects_query.fetch_by_key(code)
    if project is None:
        raise KeyError('Project not found.')
    if project[projects_query.TYPE] != projects_query.COLLECTION:
        raise ValueError('Requirements editor needs an edited-volume project.')
    return {field: project[field]
            for field in projects_query.REQUIREMENT_FIELDS}


@editor.get('/api/editor/projects/<code>/requirements')
def read_requirements(code):
    """Read the requirements shared by all authors in an edited volume."""
    return jsonify(requirements=_volume_requirements(code))


@editor.post('/api/editor/projects/<code>/requirements')
def save_requirements(code):
    """Save requirement flags without changing other project fields."""
    _volume_requirements(code)
    changes = _payload()
    unknown = set(changes) - set(projects_query.REQUIREMENT_FIELDS)
    if not changes or unknown:
        raise ValueError('Send only project requirement settings.')
    if not projects_query.update(code, changes):
        raise OSError('Could not update project requirements.')
    return jsonify(requirements=_volume_requirements(code))
