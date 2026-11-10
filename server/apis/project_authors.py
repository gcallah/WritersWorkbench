"""Project-author endpoints."""
import werkzeug.exceptions as wz
from flask import request
from flask_restx import Resource, fields

import projects.person_project as pp

from server.apis.common import check_access
from server.apis.projects import (
    PROJECTS,
    fetch_project,
    proj_parser,
    projects,
)

AUTHORS = 'authors'
PROJ_AUTHORS_W_NS = f'/{PROJECTS}/{AUTHORS}'

AUTHOR_LIST_FLDS = projects.model('AuthorList', {
    AUTHORS: fields.List(fields.String),
})


@projects.route(f'/{AUTHORS}/<code>')
@projects.expect(proj_parser)
class ProjectAuthors(Resource):
    def get(self, code):
        """Returns the project's authors, sorted by name."""
        check_access(request)
        fetch_project(code)
        return {AUTHORS: pp.fetch_authors(code)}

    @projects.expect(AUTHOR_LIST_FLDS)
    def put(self, code):
        """Makes the project's authors exactly this list of names."""
        check_access(request)
        fetch_project(code)
        names = (request.json or {}).get(AUTHORS)
        try:
            return {AUTHORS: pp.set_authors(code, names)}
        except ValueError as err:
            raise wz.NotAcceptable(str(err))
