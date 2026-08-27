"""
Aggregate all of the api namespaces.
"""
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


def get_api_obj():
    return api
