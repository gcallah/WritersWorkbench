"""
This module naturally will import from lots of places, but I do hope we can cut
back some of these imports!
"""
import sys

from flask import Flask, request
from flask_cors import CORS
from flask_restx import Resource, Namespace, fields
import werkzeug.exceptions as wz
from werkzeug.routing import Rule

import backendcore.api.common as acmn

from backendcore.common.constants import (  # noqa F401
    MAP,
    PASSWORD,
    AUTH_KEY,
)
from backendcore.api.constants import (  # noqa F401
    CREATE,
    DELETE,
    FIELDS,
    FORM,
    MESSAGE,
    READ,
    RETRIEVE,
    TEXT,
    UPDATE,
)

from server.apis import (  # noqa F401
    api,
    PW_RESET_TOK,
    RESET_PW,
    VALID_KEY,
    SAMPLE_SIGNUP_FLDS,
    EMAIL,
    signup,
    FIRST_NAME,
    LAST_NAME,
    ORG,
    USER_ID,
    SAMPLE_PASSWORD,
    NEW_PW,
)

from server.consts import (  # noqa F401
    ADD,
    CODE,
    IS_PERMITTED,
    LIST,
    LOGIN,
    REPLACE,
    SEC_MANAGER,
    SIGNUP,
    USER_DATA,
)
import server.security as sec

import projects.query as pqry

ENDPOINTS = 'Endpoints'
HELLO = 'hello'

app = Flask(__name__)
app.config['RESTX_ERROR_404_HELP'] = False
app.config['JSON_SORT_KEYS'] = False

CORS(app)
api.init_app(app)

DEF_PORT = 8000
LOCAL_HOST = '127.0.0.1'

# Endpoint constants
ENDPOINT_STR = 'Available endpoints'

# security manager
SEC_MANAGER_IS_PERMITTED_W_NS = f'/{SEC_MANAGER}/{IS_PERMITTED}'
SEC_MANAGER_RETRIEVE_W_NS = f'/{SEC_MANAGER}/{RETRIEVE}'

# User data
SIGNUP_W_NS = f'/{USER_DATA}/{SIGNUP}'
LOGIN_W_NS = f'/{USER_DATA}/{LOGIN}'
PW_RESET_TOK_W_NS = f'/{USER_DATA}/{PW_RESET_TOK}'
RESET_PW_W_NS = f'/{USER_DATA}/{RESET_PW}'
VALID_KEY_W_NS = f'/{USER_DATA}/{VALID_KEY}'

# Projects
PROJECTS = 'Projects'
PROJ_CREATE_W_NS = f'/{PROJECTS}/{CREATE}'
PROJ_READ_W_NS = f'/{PROJECTS}/{READ}'
PROJ_RETRIEVE_W_NS = f'/{PROJECTS}/{RETRIEVE}'
PROJ_UPDATE_W_NS = f'/{PROJECTS}/{UPDATE}'
PROJ_DELETE_W_NS = f'/{PROJECTS}/{DELETE}'

endpoints = Namespace(ENDPOINTS, 'Getting data about our endpoints.')
api.add_namespace(endpoints)

projects = Namespace(PROJECTS, 'Creating, reading, updating, and deleting '
                     + 'projects.')
api.add_namespace(projects)

# For the frontend:
ENDPOINTS_READ = {
    'AuthKey': VALID_KEY_W_NS,
    'IsValidUser': SEC_MANAGER_IS_PERMITTED_W_NS,
    'Login': LOGIN_W_NS,
    'ProjectCreate': PROJ_CREATE_W_NS,
    'ProjectDelete': PROJ_DELETE_W_NS,
    'ProjectRetrieve': PROJ_RETRIEVE_W_NS,
    'ProjectUpdate': PROJ_UPDATE_W_NS,
    'ProjectsRead': PROJ_READ_W_NS,
    'ResetPW': RESET_PW_W_NS,
    'ResetTok': PW_RESET_TOK_W_NS,
    'SecurityManager': SEC_MANAGER_RETRIEVE_W_NS,
    'Signup': SIGNUP_W_NS,
}


SUCCESS = 0

print(sys.path)


@api.route(f'/{HELLO}')
class Hello(Resource):
    """
    A simple endpoint to ping and see if the server is running.
    """
    def get(self):
        """
        Responds with {MESSAGE: "Hello, World!"}
        """
        return {MESSAGE: "Hello, World!"}

    def post(self):
        """
        Just testing having post and get in the same class.
        """
        return {MESSAGE: "Hello, World!"}


EP_READ_KEY = 'Endpoint Map'


# Leave this map for frontend.
@endpoints.route(f'/{MAP}')
class EndpointsRead(Resource):
    """
    A mapping of names to endpoints for the front end.
    """
    def get(self):
        """
        Returns a map of meaningful names for endpoints to URLs.
        """
        return {EP_READ_KEY: ENDPOINTS_READ}


@endpoints.route(f'/{READ}')
class Endpoints(Resource):
    """
    This endpoint lists all of our endpoints.
    For this endpoint only, it is OK to have lots of code in here, since
    this endpoint deals with endpoints.
    """
    def get(self):
        """
        List our endpoints and their documentation.
        """
        invalid_rules = [
            "/",
            "/swagger.json",
            "/swaggerui/<path:filename>",
            "/static/<path:filename>"
        ]

        rules = list(rule for rule in app.url_map.iter_rules())
        rules = filter(lambda r: r.rule not in invalid_rules, rules)
        endpoints = dict()
        for rule in rules:
            endpoints[rule.rule] = self._rule_docs(rule)
        return {ENDPOINT_STR: endpoints}

    @staticmethod
    def _rule_docs(rule: Rule):
        """
        For the given rule, assemble all supported HTTP methods and their
        documentation.
        """
        rule_class = app.view_functions[rule.endpoint].view_class
        methods = list(app.view_functions[rule.endpoint].methods)
        methods = map(lambda x: x.lower(), methods)
        method_dict = {}
        for m in methods:
            rule_func = getattr(rule_class, m)
            doc = rule_func.__doc__.strip() if rule_func.__doc__ else None
            method_dict[m] = doc
        return method_dict


# Every projects endpoint takes the auth key in the headers and the user
# name as a URL parameter.
proj_parser = projects.parser()
proj_parser.add_argument(AUTH_KEY, location='headers', required=True)
proj_parser.add_argument(pqry.USER, location='args', required=True)

PROJECT_FLDS = projects.model('Project', {
    pqry.NAME: fields.String,
    pqry.TYPE: fields.String,
})


def check_access(req) -> str:
    """
    Makes sure the request has a user name and an auth key, and that
    security allows them. Returns the user name.
    """
    user = req.args.get(pqry.USER)
    if not user:
        raise wz.BadRequest(f'Missing parameter: {pqry.USER}')
    auth_key = acmn.get_auth_key_from_request(req)
    if not auth_key:
        raise wz.Unauthorized('Auth key missing from headers.')
    if not sec.is_allowed(user, auth_key):
        raise wz.Forbidden('Action not permitted.')
    return user


def fetch_project(code: str) -> dict:
    """
    Returns the project with this code, or raises NotFound.
    """
    project = pqry.fetch_by_key(code)
    if project is None:
        raise wz.NotFound(f'No project with {CODE} {code}')
    return project


PROJECTS_READ = 'Projects'


@projects.route(f'/{CREATE}')
@projects.expect(proj_parser)
class ProjectCreate(Resource):
    @projects.expect(PROJECT_FLDS)
    def post(self):
        """
        Creates a project belonging to the user; returns its code.
        """
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
        """
        Returns the user's projects, keyed by code.
        """
        user = check_access(request)
        return {PROJECTS_READ: pqry.fetch_by_user(user)}


@projects.route(f'/{RETRIEVE}/<code>')
@projects.expect(proj_parser)
class ProjectRetrieve(Resource):
    def get(self, code):
        """
        Returns the project with this code.
        """
        check_access(request)
        return fetch_project(code)


@projects.route(f'/{UPDATE}/<code>')
@projects.expect(proj_parser)
class ProjectUpdate(Resource):
    @projects.expect(PROJECT_FLDS)
    def put(self, code):
        """
        Updates the project with this code.
        """
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
        """
        Deletes the project with this code.
        """
        check_access(request)
        fetch_project(code)
        pqry.delete(code)
        return {MESSAGE: 'Project deleted.'}
