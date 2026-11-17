"""Endpoints that describe the API itself."""
from flask import current_app
from flask_restx import Namespace, Resource
from werkzeug.routing import Rule

from backendcore.api.constants import (
    IS_PERMITTED,
    LOGIN,
    READ,
    RETRIEVE,
    SEC_MANAGER,
    SIGNUP,
    USER_DATA,
)
from backendcore.common.constants import MAP
from backendcore.api.user_data import (
    PW_RESET_TOK,
    RESET_PW,
    VALID_KEY,
)
from server.apis import api
from server.apis.projects import (
    PROJ_CREATE_W_NS,
    PROJ_DELETE_W_NS,
    PROJ_READ_W_NS,
    PROJ_RETRIEVE_W_NS,
    PROJ_UPDATE_W_NS,
)
from server.apis.users import (
    USER_CREATE_W_NS,
    USER_DELETE_W_NS,
    USER_READ_W_NS,
    USER_RETRIEVE_W_NS,
    USER_UPDATE_W_NS,
)

ENDPOINTS = 'Endpoints'
ENDPOINT_STR = 'Available endpoints'
EP_READ_KEY = 'Endpoint Map'

SEC_MANAGER_IS_PERMITTED_W_NS = f'/{SEC_MANAGER}/{IS_PERMITTED}'
SEC_MANAGER_RETRIEVE_W_NS = f'/{SEC_MANAGER}/{RETRIEVE}'
SIGNUP_W_NS = f'/{USER_DATA}/{SIGNUP}'
LOGIN_W_NS = f'/{USER_DATA}/{LOGIN}'
PW_RESET_TOK_W_NS = f'/{USER_DATA}/{PW_RESET_TOK}'
RESET_PW_W_NS = f'/{USER_DATA}/{RESET_PW}'
VALID_KEY_W_NS = f'/{USER_DATA}/{VALID_KEY}'

endpoints = Namespace(ENDPOINTS, 'Getting data about our endpoints.')
api.add_namespace(endpoints)

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


@endpoints.route(f'/{MAP}')
class EndpointsRead(Resource):
    """A mapping of names to endpoints for the front end."""

    def get(self):
        """Returns a map of meaningful names for endpoints to URLs."""
        return {EP_READ_KEY: ENDPOINTS_READ}


@endpoints.route(f'/{READ}')
class Endpoints(Resource):
    """Lists all of our endpoints and their documentation."""

    def get(self):
        """List our endpoints and their documentation."""
        invalid_rules = {
            "/",
            "/swagger.json",
            "/swaggerui/<path:filename>",
            "/static/<path:filename>",
        }

        endpoint_docs = {}
        for rule in current_app.url_map.iter_rules():
            if rule.rule not in invalid_rules:
                endpoint_docs.setdefault(rule.rule, {}).update(
                    self._rule_docs(rule))
        return {ENDPOINT_STR: endpoint_docs}

    @staticmethod
    def _rule_docs(rule: Rule):
        """Assemble the supported HTTP methods and their documentation."""
        view = current_app.view_functions[rule.endpoint]
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
