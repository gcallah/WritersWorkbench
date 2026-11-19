"""Project endpoints."""
import werkzeug.exceptions as wz
from flask import jsonify, make_response, request
from flask_restx import Namespace, Resource, fields

import projects.query as pqry

from backendcore.api.constants import (
    CREATE,
    DELETE,
    MESSAGE,
    READ,
    RETRIEVE,
    UPDATE,
)
from backendcore.common.constants import AUTH_KEY
from server.apis import api
from server.apis.common import check_access
from server.consts import CODE
from server.editor import editor_login_problem

PROJECTS = 'Projects'
PROJ_CREATE_W_NS = f'/{PROJECTS}/{CREATE}'
PROJ_READ_W_NS = f'/{PROJECTS}/{READ}'
PROJ_RETRIEVE_W_NS = f'/{PROJECTS}/{RETRIEVE}'
PROJ_UPDATE_W_NS = f'/{PROJECTS}/{UPDATE}'
PROJ_DELETE_W_NS = f'/{PROJECTS}/{DELETE}'
REQUIREMENTS = 'requirements'
PROJ_REQUIREMENTS_W_NS = f'/{PROJECTS}/{REQUIREMENTS}'
PROJECTS_READ = 'Projects'

projects = Namespace(PROJECTS, 'Creating, reading, updating, and deleting '
                     + 'projects.')
api.add_namespace(projects)

# Every projects endpoint takes the auth key in the headers and the user
# name as a URL parameter.
proj_parser = projects.parser()
proj_parser.add_argument(AUTH_KEY, location='headers', required=True)
proj_parser.add_argument(pqry.USER, location='args', required=True)

PROJECT_FLDS = projects.model('Project', {
    pqry.NAME: fields.String,
    pqry.TYPE: fields.String(description='Set at creation; cannot change.'),
    **dict.fromkeys(pqry.REQUIREMENT_FIELDS, fields.Boolean),
})


def fetch_project(code: str) -> dict:
    """Returns the project with this code, or raises NotFound."""
    project = pqry.fetch_by_key(code)
    if project is None:
        raise wz.NotFound(f'No project with {CODE} {code}')
    return project


@projects.route(f'/{CREATE}')
@projects.expect(proj_parser)
class ProjectCreate(Resource):
    @projects.expect(PROJECT_FLDS)
    def post(self):
        """Creates a project belonging to the user; returns its code."""
        user = check_access(request)
        project = dict(request.json or {})
        project[pqry.USER] = user
        try:
            return {CODE: pqry.add(project)}
        except ValueError as err:
            raise wz.NotAcceptable(str(err))


@projects.route(f'/{READ}')
@projects.expect(proj_parser)
class ProjectsRead(Resource):
    def get(self):
        """Returns the user's projects, keyed by code."""
        user = check_access(request)
        return {PROJECTS_READ: pqry.fetch_by_user(user)}


@projects.route(f'/{RETRIEVE}/<code>')
@projects.expect(proj_parser)
class ProjectRetrieve(Resource):
    def get(self, code):
        """Returns the project with this code."""
        check_access(request)
        return fetch_project(code)


@projects.route(f'/{UPDATE}/<code>')
@projects.expect(proj_parser)
class ProjectUpdate(Resource):
    @projects.expect(PROJECT_FLDS)
    def put(self, code):
        """Updates the project with this code."""
        check_access(request)
        fetch_project(code)
        try:
            pqry.update(code, request.json or {})
        except ValueError as err:
            raise wz.NotAcceptable(str(err))
        return {MESSAGE: 'Project updated.'}


def _private_json(body, status=200):
    """
    Send back JSON that browsers shouldn't save a copy of, since it's
    only for logged-in editors.
    """
    response = make_response(jsonify(body), status)
    response.headers['Cache-Control'] = 'no-store'
    return response


def _private_json_error(problem):
    """Turn a login-check error into a response browsers won't save."""
    response = make_response(problem)
    response.headers['Cache-Control'] = 'no-store'
    return response


def project_requirements(code) -> dict:
    """
    Returns what each contributor to this project must provide. Raises
    KeyError if the project doesn't exist, or ValueError if it isn't an
    edited volume or journal issue (the types that have contributors).
    """
    project = pqry.fetch_by_key(code)
    if project is None:
        raise KeyError('Project not found.')
    if not pqry.is_multi_author(project[pqry.TYPE]):
        raise ValueError('Requirements need a multi-author project.')
    return {field: project[field] for field in pqry.REQUIREMENT_FIELDS}


@projects.route(f'/{REQUIREMENTS}/<code>')
class ProjectRequirements(Resource):
    """
    What each contributor must provide (a bio, permission to publish, an
    address). Moved here from /api/editor in issue #22. It uses the same
    login as the web pages, since the Contributors page calls it.
    """
    def get(self, code):
        """
        Returns what each contributor to this project must provide.
        """
        problem = editor_login_problem()
        if problem is not None:
            return _private_json_error(problem)
        try:
            return _private_json({REQUIREMENTS: project_requirements(code)})
        except KeyError as err:
            return _private_json({'error': err.args[0]}, 404)
        except ValueError as err:
            return _private_json({'error': str(err)}, 400)

    def put(self, code):
        """
        Saves what each contributor to this project must provide.
        """
        problem = editor_login_problem()
        if problem is not None:
            return _private_json_error(problem)
        try:
            project_requirements(code)
            changes = request.get_json(silent=True)
            # Only the requirement settings may be changed here.
            if (not isinstance(changes, dict) or not changes
                    or set(changes) - set(pqry.REQUIREMENT_FIELDS)):
                raise ValueError('Send only project requirement settings.')
            if not pqry.update(code, changes):
                return _private_json(
                    {'error': 'Could not update project requirements.'}, 500)
            return _private_json({REQUIREMENTS: project_requirements(code)})
        except KeyError as err:
            return _private_json({'error': err.args[0]}, 404)
        except ValueError as err:
            return _private_json({'error': str(err)}, 400)


@projects.route(f'/{DELETE}/<code>')
@projects.expect(proj_parser)
class ProjectDelete(Resource):
    def delete(self, code):
        """Deletes the project with this code."""
        check_access(request)
        fetch_project(code)
        pqry.delete(code)
        return {MESSAGE: 'Project deleted.'}
