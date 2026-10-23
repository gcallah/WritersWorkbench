"""
This module naturally will import from lots of places, but I do hope we can cut
back some of these imports!
"""
import os
import secrets
from pathlib import Path

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
from server.editor import editor
from server.web import web

import projects.query as pqry
import users.query as uqry

ENDPOINTS = 'Endpoints'
HELLO = 'hello'

app = Flask(__name__)
app.config['RESTX_ERROR_404_HELP'] = False
app.config['JSON_SORT_KEYS'] = False
app.config['EDITOR_USERNAME'] = os.getenv('WRITERS_EDITOR_USERNAME', 'editor')
app.config['EDITOR_PASSWORD'] = os.getenv('WRITERS_EDITOR_PASSWORD')
app.config['CONTRIBUTOR_DATA_DIR'] = os.getenv(
    'WRITERS_DATA_DIR', str(Path(app.instance_path) / 'contributors'))
app.register_blueprint(editor)
app.register_blueprint(web)

# The web pages use flash() messages, which Flask keeps in a signed cookie.
# Signing needs a secret key. Set WRITERS_SECRET_KEY on a real server;
# locally we make up a random one each time the server starts.
app.secret_key = os.getenv('WRITERS_SECRET_KEY') or secrets.token_hex(32)

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

# Users
USERS = 'Users'
USER_CREATE_W_NS = f'/{USERS}/{CREATE}'
USER_READ_W_NS = f'/{USERS}/{READ}'
USER_RETRIEVE_W_NS = f'/{USERS}/{RETRIEVE}'
USER_UPDATE_W_NS = f'/{USERS}/{UPDATE}'
USER_DELETE_W_NS = f'/{USERS}/{DELETE}'

endpoints = Namespace(ENDPOINTS, 'Getting data about our endpoints.')
api.add_namespace(endpoints)

projects = Namespace(PROJECTS, 'Creating, reading, updating, and deleting '
                     + 'projects.')
api.add_namespace(projects)

users = Namespace(USERS, 'Creating, reading, updating, and deleting users.')
api.add_namespace(users)

# For the frontend:
ENDPOINTS_READ = {
    'ContributorEditor': '/editor',
    'WebHome': '/web/',
    'WebProjects': '/web/projects',
    'Contributors': '/api/contributors',
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
    'UserCreate': USER_CREATE_W_NS,
    'UserDelete': USER_DELETE_W_NS,
    'UserRetrieve': USER_RETRIEVE_W_NS,
    'UserUpdate': USER_UPDATE_W_NS,
    'UsersRead': USER_READ_W_NS,
}


SUCCESS = 0


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

        endpoint_docs = {}
        for rule in app.url_map.iter_rules():
            if rule.rule not in invalid_rules:
                endpoint_docs.setdefault(rule.rule, {}).update(
                    self._rule_docs(rule))
        return {ENDPOINT_STR: endpoint_docs}

    @staticmethod
    def _rule_docs(rule: Rule):
        """
        For the given rule, assemble all supported HTTP methods and their
        documentation.
        """
        view = app.view_functions[rule.endpoint]
        if not hasattr(view, 'view_class'):
            doc = view.__doc__.strip() if view.__doc__ else None
            return {
                method.lower(): doc for method in rule.methods
                if method not in {'HEAD', 'OPTIONS'}
            }
        method_docs = {}
        for method in view.methods:
            method_name = method.lower()
            rule_func = getattr(view.view_class, method_name)
            doc = rule_func.__doc__.strip() if rule_func.__doc__ else None
            method_docs[method_name] = doc
        return method_docs


# Every projects endpoint takes the auth key in the headers and the user
# name as a URL parameter.
proj_parser = projects.parser()
proj_parser.add_argument(AUTH_KEY, location='headers', required=True)
proj_parser.add_argument(pqry.USER, location='args', required=True)

PROJECT_FLDS = projects.model('Project', {
    pqry.NAME: fields.String,
    pqry.TYPE: fields.String,
    pqry.REQUIRES_BIO: fields.Boolean,
    pqry.REQUIRES_PERMISSION: fields.Boolean,
    pqry.REQUIRES_ADDRESS: fields.Boolean,
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


USER_FLDS = users.model('User', {
    uqry.NAME: fields.String,
    uqry.AUTH_KEY: fields.String,
    uqry.PASSWORD: fields.String,
})
USERS_READ = 'Users'
CURRENT_PW = 'current_password'


def public_user(user: dict) -> dict:
    """
    Returns a copy of the user without the auth key, which is a secret.
    """
    return {key: val for key, val in user.items() if key != uqry.AUTH_KEY}


def fetch_user(user_id: str) -> dict:
    """
    Returns the user with this id, or raises NotFound.
    """
    user = uqry.fetch_by_key(user_id)
    if user is None:
        raise wz.NotFound(f'No user with id {user_id}')
    return user


def check_owner(req, user: dict):
    """
    Only a user may change their own record: the auth key in the
    headers must be the one stored for them.
    """
    if acmn.get_auth_key_from_request(req) != user.get(uqry.AUTH_KEY):
        raise wz.Forbidden('You may only change your own user record.')


@users.route(f'/{CREATE}')
@users.expect(proj_parser)
class UserCreate(Resource):
    @users.expect(USER_FLDS)
    def post(self):
        """
        Creates a user from a name, auth key and password; returns its id.
        """
        check_access(request)
        try:
            return {uqry.ID: uqry.add(dict(request.json or {}))}
        except ValueError as err:
            raise wz.NotAcceptable(str(err))


@users.route(f'/{READ}')
@users.expect(proj_parser)
class UsersRead(Resource):
    def get(self):
        """
        Returns all users keyed by id, without their auth keys.
        """
        check_access(request)
        return {USERS_READ: {user_id: public_user(user) for user_id, user
                             in uqry.fetch_dict().items()}}


@users.route(f'/{RETRIEVE}/<user_id>')
@users.expect(proj_parser)
class UserRetrieve(Resource):
    def get(self, user_id):
        """
        Returns the user with this id, without their auth key.
        """
        check_access(request)
        return public_user(fetch_user(user_id))


@users.route(f'/{UPDATE}/<user_id>')
@users.expect(proj_parser)
class UserUpdate(Resource):
    @users.expect(USER_FLDS)
    def put(self, user_id):
        """
        Updates the user with this id. Only that user may do so, and a
        password change also needs the current password, if one is set.
        """
        check_access(request)
        user = fetch_user(user_id)
        check_owner(request, user)
        changes = dict(request.json or {})
        current_pw = changes.pop(CURRENT_PW, None)
        if (uqry.PASSWORD in changes and uqry.has_password(user_id)
                and not uqry.check_password(user_id, current_pw)):
            raise wz.Forbidden('Current password is wrong.')
        try:
            uqry.update(user_id, changes)
        except ValueError as err:
            raise wz.NotAcceptable(str(err))
        return {MESSAGE: 'User updated.'}


@users.route(f'/{DELETE}/<user_id>')
@users.expect(proj_parser)
class UserDelete(Resource):
    def delete(self, user_id):
        """
        Deletes the user with this id. Only that user may do so.
        """
        check_access(request)
        check_owner(request, fetch_user(user_id))
        uqry.delete(user_id)
        return {MESSAGE: 'User deleted.'}
