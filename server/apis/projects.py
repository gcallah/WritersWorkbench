"""Project endpoints."""
import werkzeug.exceptions as wz
from flask import request
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

PROJECTS = 'Projects'
PROJ_CREATE_W_NS = f'/{PROJECTS}/{CREATE}'
PROJ_READ_W_NS = f'/{PROJECTS}/{READ}'
PROJ_RETRIEVE_W_NS = f'/{PROJECTS}/{RETRIEVE}'
PROJ_UPDATE_W_NS = f'/{PROJECTS}/{UPDATE}'
PROJ_DELETE_W_NS = f'/{PROJECTS}/{DELETE}'
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
    pqry.TYPE: fields.String,
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


@projects.route(f'/{DELETE}/<code>')
@projects.expect(proj_parser)
class ProjectDelete(Resource):
    def delete(self, code):
        """Deletes the project with this code."""
        check_access(request)
        fetch_project(code)
        pqry.delete(code)
        return {MESSAGE: 'Project deleted.'}
