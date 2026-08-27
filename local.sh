#!/bin/bash

# This script runs the API server.

export PYTHONPATH=$PYTHONPATH:$(pwd)

export FLASK_ENV=development
export PROJ_DIR=$PWD
export DEBUG=1
export HOST=127.0.0.1
export PORT=8000

FLASK_APP=server.endpoints flask run --debug --host=$HOST --port=$PORT
