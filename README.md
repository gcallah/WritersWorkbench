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

## Edited-volume projects (issue #5)

The existing `collection` type is displayed as **Edited volume (multi-author)**.
Creating a project through `projects.query.add` or `/Projects/create` creates
its directory. Other project types get an empty directory; edited volumes get
these folders, following [JustifyingTheState](https://github.com/gcallah/JustifyingTheState):

- `abstracts`, `addresses`, `bios`, `chapters`, `keywords`, `permissions`
- `drafts` and `Proposal`

We copy the folder pattern, not the example book's authors or documents.
Project folders default to `instance/projects/<project-code>/`. Set
`WRITERS_PROJECTS_DIR` to change that root, consistently for both the API and
command-line use. Codes remain stable when a project is renamed. Changing a
project to `collection` also creates any missing template folders. Existing
collections created before this change get their folders on an update or first
material save.

### Contributors, files, and the existing editor

Choose a book in the new **Project** selector at `/editor`, then use the existing
Add contributor, Biography, and Submission controls. The selector lists existing
edited volumes; create books using the existing Projects API or Python data
module. The editor remains protected by the existing shared editor credentials.
This change does not add per-user login or change the project's security model.

Contributor IDs, names, project codes, and received-item flags live in the
`ProjectContributors` collection through BackEndCore, using the same database
configuration as projects. The local scripts and makefile select SQLite.
Actual materials live on disk, for example:

- `instance/projects/<project-code>/bios/<contributor-id>.txt`
- `instance/projects/<project-code>/chapters/<contributor-id>.txt`

The editor's existing `submission` means chapter text for an edited volume.
It still edits plain text, not Word or PDF documents. The existing `Bio` and
`Submission` flag names are preserved. The database also tracks `Abstract`,
`Address`, `Keywords`, and `Permission`. A flag becomes true only after that
item is saved successfully. Empty template folders do not mark items received.

The existing contributor endpoints accept `?project=<project-code>` to select
a book. `/api/editor/projects` lists the edited volumes for the authenticated
shared editor. The piece API also accepts `abstract`, `address`, `keywords`, and
`permission` as plain-text piece types for project-scoped requests.
For scripts handling actual documents, `projects.materials.save_file` accepts
bytes and one of `.txt`, `.md`, `.docx`, or `.pdf` (up to 10 MB). It stores those
bytes without converting or executing them. The browser's two existing text
tabs have not been expanded into a document-upload interface.

**Existing data:** select **Unassigned contributors (existing data)** to keep
using the original file-backed editor records. Requests without a project
parameter keep their previous behavior. No existing contributor is guessed into
a book, moved, or deleted. A future explicit migration can associate old data.

**Retention and failures:** project deletion removes the project record, but
retains its documents and contributor records for recovery. It does not delete
manuscripts automatically. Changing a collection to another type also retains
its material, but removes it from the edited-volume selector. Back up both the
database and the project files. File writes replace files atomically; database
and file writes are not a single transaction. If the file succeeds but the
receipt update fails, the request reports failure and can be retried. As with
the original editor, use a single server process for this initial version.

### Small local example

With the virtual environment active, from the repository root:

```bash
export PYTHONPATH="$PWD"
export DATABASE=sqlite
export SQLITE_LOC="$PWD/database"
python - <<'PYTHON'
from projects import query
code = query.add({
    "name": "My edited volume",
    "user": "umeraliabbasi",
    "type": query.COLLECTION,
})
print("Created project:", code)
PYTHON
```

Start the editor with the credentials shown above and `./local.sh`, then open
`http://127.0.0.1:8000/editor`. Select the book, add a contributor, save a bio,
and switch books to verify that their contributors stay separate. This example
creates a real development record, so run it only when you want a new book.

Run `make all_tests` with `PYTHONPATH` set and the virtual environment active.
The tests use temporary project folders, separate from real manuscripts.

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

issue-4-web-interface
### Running on Windows

From the Command Prompt, in the repo folder, install the requirements once:

```
pip install -r requirements.txt
```

Then start the web interface with:

```
web.bat
```

It runs on port 8002. Open `http://127.0.0.1:8002/web/` and log in as `editor`
with the password it asks you to choose.


### Author requirements

In `/editor`, select an edited-volume project to choose whether each author
must provide a biography, permission to publish, or an address. Click
**Save requirements** to store the choices. These settings are separate from
whether an author has already submitted each item.
See [project requirement settings](docs/project_requirements.md) for API fields,
compatibility notes and integration instructions.
master
