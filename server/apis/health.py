"""Health-check endpoints."""
from flask_restx import Resource

from backendcore.api.constants import MESSAGE
from server.apis import api

HELLO = 'hello'


@api.route(f'/{HELLO}')
class Hello(Resource):
    """A simple endpoint to ping and see if the server is running."""

    def get(self):
        """Responds with {MESSAGE: \"Hello, World!\"}."""
        return {MESSAGE: "Hello, World!"}

    def post(self):
        """Just testing having post and get in the same class."""
        return {MESSAGE: "Hello, World!"}
