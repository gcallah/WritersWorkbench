"""Create the Flask application and expose endpoint compatibility imports."""
import os
import secrets
from pathlib import Path

from flask import Flask, request  # noqa: F401
from flask_cors import CORS
import werkzeug.exceptions as wz  # noqa: F401

from backendcore.api.constants import (  # noqa: F401
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
from backendcore.common.constants import (  # noqa: F401
    AUTH_KEY,
    MAP,
    PASSWORD,
)
from server.apis import (  # noqa: F401
    EMAIL,
    FIRST_NAME,
    LAST_NAME,
    NEW_PW,
    ORG,
    PW_RESET_TOK,
    RESET_PW,
    SAMPLE_PASSWORD,
    SAMPLE_SIGNUP_FLDS,
    USER_ID,
    VALID_KEY,
    api,
    signup,
)
from server.apis.common import check_access  # noqa: F401
from server.apis.endpoint_info import (  # noqa: F401
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
from server.apis.project_authors import (  # noqa: F401
    AUTHORS,
    PROJ_AUTHORS_W_NS,
    ProjectAuthors,
)
from server.apis.health import HELLO, Hello  # noqa: F401
from server.apis.projects import (  # noqa: F401
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
from server.apis.users import (  # noqa: F401
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
from server.consts import (  # noqa: F401
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
import projects.query as pqry  # noqa: F401
import users.query as uqry  # noqa: F401

from server.editor import editor
from server.web import web

DEF_PORT = 8000
LOCAL_HOST = '127.0.0.1'
SUCCESS = 0

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
