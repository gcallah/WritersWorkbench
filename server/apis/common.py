"""Helpers shared by server API endpoint modules."""
import werkzeug.exceptions as wz

import backendcore.api.common as acmn
import projects.query as pqry
import server.security as sec


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
