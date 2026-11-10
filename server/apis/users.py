"""User endpoints."""
import werkzeug.exceptions as wz
from flask import request
from flask_restx import Namespace, Resource, fields

import projects.query as pqry
import users.query as uqry

import backendcore.api.common as acmn
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

USERS = 'Users'
USER_CREATE_W_NS = f'/{USERS}/{CREATE}'
USER_READ_W_NS = f'/{USERS}/{READ}'
USER_RETRIEVE_W_NS = f'/{USERS}/{RETRIEVE}'
USER_UPDATE_W_NS = f'/{USERS}/{UPDATE}'
USER_DELETE_W_NS = f'/{USERS}/{DELETE}'
USERS_READ = 'Users'
CURRENT_PW = 'current_password'

users = Namespace(USERS, 'Creating, reading, updating, and deleting users.')
api.add_namespace(users)

user_parser = users.parser()
user_parser.add_argument(AUTH_KEY, location='headers', required=True)
user_parser.add_argument(pqry.USER, location='args', required=True)

USER_FLDS = users.model('User', {
    uqry.NAME: fields.String,
    uqry.AUTH_KEY: fields.String,
    uqry.PASSWORD: fields.String,
})


def public_user(user: dict) -> dict:
    """Returns a copy of the user without the auth key, which is a secret."""
    return {key: val for key, val in user.items() if key != uqry.AUTH_KEY}


def fetch_user(user_id: str) -> dict:
    """Returns the user with this id, or raises NotFound."""
    user = uqry.fetch_by_key(user_id)
    if user is None:
        raise wz.NotFound(f'No user with id {user_id}')
    return user


def check_owner(req, user: dict):
    """Require the auth key in the request to match the stored user key."""
    if acmn.get_auth_key_from_request(req) != user.get(uqry.AUTH_KEY):
        raise wz.Forbidden('You may only change your own user record.')


@users.route(f'/{CREATE}')
@users.expect(user_parser)
class UserCreate(Resource):
    @users.expect(USER_FLDS)
    def post(self):
        """Creates a user and returns its id."""
        check_access(request)
        try:
            return {uqry.ID: uqry.add(dict(request.json or {}))}
        except ValueError as err:
            raise wz.NotAcceptable(str(err))


@users.route(f'/{READ}')
@users.expect(user_parser)
class UsersRead(Resource):
    def get(self):
        """Returns all users keyed by id, without their auth keys."""
        check_access(request)
        return {USERS_READ: {user_id: public_user(user) for user_id, user
                             in uqry.fetch_dict().items()}}


@users.route(f'/{RETRIEVE}/<user_id>')
@users.expect(user_parser)
class UserRetrieve(Resource):
    def get(self, user_id):
        """Returns the user with this id, without their auth key."""
        check_access(request)
        return public_user(fetch_user(user_id))


@users.route(f'/{UPDATE}/<user_id>')
@users.expect(user_parser)
class UserUpdate(Resource):
    @users.expect(USER_FLDS)
    def put(self, user_id):
        """Updates the user; password changes require the current password."""
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
@users.expect(user_parser)
class UserDelete(Resource):
    def delete(self, user_id):
        """Deletes the user with this id. Only that user may do so."""
        check_access(request)
        check_owner(request, fetch_user(user_id))
        uqry.delete(user_id)
        return {MESSAGE: 'User deleted.'}
