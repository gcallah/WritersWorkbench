#!/bin/bash
# This runs on PythonAnywhere servers: fetches new code,
# Installs needed packages, and restarts the server.

touch rebuild
echo "Rebuilding $PA_DOMAIN"

echo "Starting ssh"
eval "$(ssh-agent -s)"

echo "Activate the virtual env $VENV for user $PA_USER"
source /home/$PA_USER/.virtualenvs/$VENV/bin/activate

make rebuild
