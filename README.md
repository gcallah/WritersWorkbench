# The Writer's Workbench

Our intention here is to create a suite of tools for professional writers.

## Contributor Editor

The editor is at `/editor`. Add a contributor, select **Biography** or
**Submission**, enter the text, and select **Save changes**. Saving a biography
sets that contributor's `Bio` field to `true`; saving a submission sets
`Submission` to `true`. Existing text loads when selecting a contributor or tab.
Each contributor has one biography and one submission; saving edits replaces
that piece. Unsaved drafts prompt before switching contributors or tabs.

In the activated Python environment, configure these variables and start Flask:

```bash
export WRITERS_EDITOR_USERNAME=editor
read -rs -p 'Editor password: ' WRITERS_EDITOR_PASSWORD
echo
export WRITERS_EDITOR_PASSWORD
export OUR_NAME=WritersWorkbench
python -m flask --app server.endpoints run --host 127.0.0.1 --port 8001
```

Open `http://127.0.0.1:8001/editor` and enter the configured username and password
in the browser's authentication prompt. Editor access is disabled unless
`WRITERS_EDITOR_PASSWORD` is set. These credentials are separate from the
starter API's user accounts. Use HTTPS and a production WSGI server for any
non-local deployment; the Flask development server is only for local use.

Set `WRITERS_DATA_DIR` to a writable persistent directory if needed. By default,
data lives in Flask's ignored `instance/contributors` directory. Each contributor
gets a generated ID directory containing `contributor.json`, `bio.txt`, and
`submission.txt` (when received). Text is saved as UTF-8, up to 100,000 characters
per piece. Back up this directory; it is separate from MongoDB. The file-backed
editor is intended for a single server process, with in-process write locking.

Authenticated JSON endpoints are `GET/POST /api/contributors` and
`GET/POST /api/contributors/<id>/pieces/<type>`, where type is `bio` or
`submission`. Creation accepts `{"name": "Author name"}`; piece saving accepts
`{"text": "Piece text"}` and returns the updated contributor record. Browser
writes must be same-origin. Failed saves keep the browser draft available.

## GitHub Actions

The active workflow is `.github/workflows/main.yml`. It runs on pushes and pull
requests targeting `master` or `main`, or manually from **Actions > Python CI >
Run workflow**. The workflow installs Python 3.13 and the development dependencies,
starts MongoDB, and runs the server lint checks and tests with `make all_tests`.
BackEndCore is installed over HTTPS from its public repository; no SSH secret or
deployment environment is required.

Commit and push the workflow and requirements changes, then open the run in the
Actions tab. A successful run has a green check; expand the first failed step to
see its error. The root `main.yml` is a sample, not the workflow GitHub executes.

## Local Tests In WSL

Run these commands in Ubuntu WSL, not PowerShell. Python 3, its `venv` module,
Git, Make, and `mongod` must be installed. The setup uses persistent directories
under your Linux home directory, rather than `/tmp`.

Set up Python 3.13 and the test dependencies once:

```bash
cd /mnt/c/Users/Owner/WritersWorkbench
mkdir -p "$HOME/.local/share/writersworkbench"
python3 -m venv "$HOME/.local/share/writersworkbench/bootstrap"
"$HOME/.local/share/writersworkbench/bootstrap/bin/python" -m pip install uv
"$HOME/.local/share/writersworkbench/bootstrap/bin/uv" venv --python 3.13 --managed-python "$HOME/.local/share/writersworkbench/venv"
"$HOME/.local/share/writersworkbench/bootstrap/bin/uv" pip install --python "$HOME/.local/share/writersworkbench/venv/bin/python" -r requirements-dev.txt
```

Run tests in a subshell that stops on errors and shuts down its test database:

```bash
(
	set -eu
	cd /mnt/c/Users/Owner/WritersWorkbench
	source "$HOME/.local/share/writersworkbench/venv/bin/activate"
	mkdir -p "$HOME/.local/share/writersworkbench/mongodb"
	mongod --dbpath "$HOME/.local/share/writersworkbench/mongodb" --bind_ip 127.0.0.1 --port 27017 --logpath "$HOME/.local/share/writersworkbench/mongodb/mongod.log" --fork
	trap 'mongod --shutdown --dbpath "$HOME/.local/share/writersworkbench/mongodb" >/dev/null 2>&1' EXIT
	export PYTHONPATH="$PWD"
	export LOCAL_MONGO=1 TEST_DB=1 OUR_NAME=WritersWorkbench
	make all_tests
)
```

Port 27017 must be free before starting this dedicated database. If MongoDB fails
to start, inspect `$HOME/.local/share/writersworkbench/mongodb/mongod.log`.
