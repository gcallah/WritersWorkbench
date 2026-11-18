"""Create and configure the Flask application."""
import os
import secrets
from pathlib import Path

from flask import Flask
from flask_cors import CORS
from server.apis import api

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
