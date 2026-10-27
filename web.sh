export DATABASE=sqlite
export SQLITE_LOC="$PWD/database"
export OUR_NAME=WritersWorkbench
export WRITERS_EDITOR_USERNAME=editor
export WRITERS_EDITOR_PASSWORD=callahan

python3 -m flask --app server.endpoints run --host 127.0.0.1 --port 8002
