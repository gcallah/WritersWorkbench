"""
Aggregate all of the api namespaces.
"""
import projects.query as pqry
import users.query as uqry
import werkzeug.exceptions as wz
from flask import request
from flask_restx import Api

from backendcore.api.sec_manager import api as sec_manager
from backendcore.api.user_data import api as user_data
from backendcore.api.user_data import ( # noqa F401
    NEW_PW,
    signup,
)

from backendcore.api.user_data import (# noqa F401
    FIRST_NAME,
    LAST_NAME,
    ORG,
    PW_RESET_TOK,
    RESET_PW,
    VALID_KEY,
    SAMPLE_SIGNUP_FLDS,
    EMAIL,
    USER_ID,
    SAMPLE_PASSWORD,
    NEW_PW,
)

api = Api(
    title='Minimal API Server',
    version='1.0',
    description='An API server template.',
    contact={
        'email': 'gcallah@mac.com',
        'name': 'Gene Callahan',
    },
)

api.add_namespace(sec_manager)
api.add_namespace(user_data)

from server.apis.common import check_access  # noqa: F401,E402
from server.apis.endpoint_info import (  # noqa: F401,E402
    ENDPOINTS,
    ENDPOINTS_READ,
    ENDPOINT_STR,
    EP_READ_KEY,
    Endpoints,
    EndpointsRead,
    LOGIN_W_NS,
    PW_RESET_TOK_W_NS,
    RESET_PW_W_NS,
    SEC_MANAGER_IS_PERMITTED_W_NS,
    SEC_MANAGER_RETRIEVE_W_NS,
    SIGNUP_W_NS,
    VALID_KEY_W_NS,
)
from server.apis.project_authors import (  # noqa: F401,E402
    AUTHORS,
    PROJ_AUTHORS_W_NS,
    ProjectAuthors,
)
from server.apis.health import HELLO, Hello  # noqa: F401,E402
from server.apis.projects import (  # noqa: F401,E402
    PROJECTS,
    PROJECTS_READ,
    PROJ_CREATE_W_NS,
    PROJ_DELETE_W_NS,
    PROJ_READ_W_NS,
    PROJ_RETRIEVE_W_NS,
    PROJ_UPDATE_W_NS,
    PROJECT_FLDS,
    ProjectCreate,
    ProjectDelete,
    ProjectRetrieve,
    ProjectUpdate,
    ProjectsRead,
    fetch_project,
    proj_parser,
    projects,
)
from server.apis.users import (  # noqa: F401,E402
    CURRENT_PW,
    USER_CREATE_W_NS,
    USER_DELETE_W_NS,
    USER_READ_W_NS,
    USER_RETRIEVE_W_NS,
    USER_UPDATE_W_NS,
    USERS,
    USERS_READ,
    USER_FLDS,
    UserCreate,
    UserDelete,
    UserRetrieve,
    UserUpdate,
    UsersRead,
    check_owner,
    fetch_user,
    public_user,
    users,
)
from server.consts import (  # noqa: F401,E402
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
from backendcore.api.constants import (  # noqa: F401,E402
    CREATE,
    DELETE,
    FIELDS,
    MESSAGE,
    READ,
    RETRIEVE,
    TEXT,
    UPDATE,
)
from backendcore.common.constants import (  # noqa: F401,E402
    AUTH_KEY,
    MAP,
    PASSWORD,
)


def get_api_obj():
    return api
