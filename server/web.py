"""
A simple web interface for the Writer's Workbench (issue #4).

Before this, projects could only be managed through the JSON API or by
running Python code. These pages let someone do the same things from a
browser: see all projects, create one, rename it or edit its authors, and
delete it.

The pages live under /web so they don't collide with the API's Swagger
page, which already uses "/".
"""
from secrets import compare_digest

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, url_for)

from projects import contributors, materials
import projects.person_project as pp
import projects.people as people
import projects.query as pqry
from server.editor import MAX_TOC_CHARS

# The edit form's box where the editor types one author per line.
AUTHORS_FIELD = 'authors'

# What the fill-in screens call each piece an author can provide.
PIECE_LABELS = {
    'bio': 'Biography',
    'submission': 'Submission (chapter text)',
    'abstract': 'Abstract',
    'address': 'Address',
    'keywords': 'Keywords',
    'permission': 'Permission to publish',
    'referee_report': 'Referee report',
}
# The project requirement, if any, that asks authors for each piece.
REQUIRED_BY = {
    'bio': 'requires_bio',
    'permission': 'requires_permission',
    'address': 'requires_address',
    'abstract': 'requires_abstract',
    'keywords': 'requires_keywords',
}


# A "blueprint" is a group of related pages. endpoints.py plugs it into
# the main Flask app with app.register_blueprint(web).
web = Blueprint('web', __name__, url_prefix='/web',
                template_folder='templates')


@web.before_request
def require_login():
    """
    Runs before every page in this file and asks for a username and
    password.

    For now we reuse the same shared login as the contributor editor
    (WRITERS_EDITOR_USERNAME / WRITERS_EDITOR_PASSWORD). Real per-user
    login can replace this once the user data endpoints (#2) are done.
    """
    # If no password was set up, lock the pages instead of leaving them
    # open to anyone.
    password = current_app.config.get('EDITOR_PASSWORD')
    if not password:
        return 'Web interface login is not configured.', 503

    # request.authorization holds whatever the browser's login popup sent.
    # compare_digest checks the text in a way that doesn't leak hints
    # about how close a wrong guess was.
    auth = request.authorization
    username = current_app.config['EDITOR_USERNAME']
    if (auth is None or auth.type != 'basic'
            or not compare_digest((auth.username or '').encode(),
                                  username.encode())
            or not compare_digest((auth.password or '').encode(),
                                  password.encode())):
        # 401 plus this header makes the browser show its login popup.
        return ('Login required.', 401,
                {'WWW-Authenticate': 'Basic realm="Writer\'s Workbench", '
                                     'charset="UTF-8"'})

    # For form submissions, only accept ones that came from our own site,
    # so another website can't trick a logged-in browser into deleting
    # projects.
    if request.method == 'POST' and not _same_site_form():
        return 'Cross-site form submissions are not allowed.', 403
    return None


def _same_site_form():
    """
    Checks whether a submitted form came from one of our own pages.

    Modern browsers label every request with a Sec-Fetch-Site header:
    "same-origin" means it came from our own page, "cross-site" means
    another website sent it. Other websites can't fake this label, and
    proxies (like GitHub Codespaces) pass it along unchanged, so it works
    even when the browser and server see different addresses.
    """
    fetch_site = request.headers.get('Sec-Fetch-Site')
    if fetch_site is not None:
        # "none" means the person typed the address themselves.
        return fetch_site in ('same-origin', 'none')
    # Older browsers don't send that label, so fall back to comparing
    # the address the form came from with our own address.
    origin = request.headers.get('Origin')
    return not origin or origin == request.host_url.rstrip('/')


@web.after_request
def no_caching(response):
    """Tell the browser not to save copies of these private pages."""
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response


def _current_user():
    """The name projects get saved under: the shared login name for now."""
    return current_app.config['EDITOR_USERNAME']


def _project_or_none(code):
    """Look up one project by its code. Gives back None if it isn't there."""
    return pqry.fetch_by_key(code)


@web.get('/')
def home():
    """The landing page, with links to the projects page and the editor."""
    return render_template('web/home.html')


@web.get('/projects')
def project_list():
    """Show every project, plus a form for creating a new one."""
    # Sort by name, ignoring upper/lower case, so the list is easy to scan.
    all_projects = sorted(pqry.fetch_list(),
                          key=lambda proj: proj[pqry.NAME].casefold())
    # Each project's author names, so the list can show who is on it.
    authors_by_code = {
        proj[pqry.CODE]: [author[people.NAME]
                          for author in pp.fetch_authors(proj[pqry.CODE])]
        for proj in all_projects
    }
    return render_template('web/projects.html',
                           projects=all_projects,
                           components=pqry.AUTHOR_COMPONENTS,
                           collection_type=pqry.COLLECTION,
                           authors_by_code=authors_by_code,
                           type_choices=pqry.get_type_choices())


@web.post('/projects')
def project_create():
    """Handle the "Create project" form."""
    # request.form holds what the person typed into the form.
    new_project = {
        pqry.NAME: request.form.get(pqry.NAME, '').strip(),
        pqry.TYPE: request.form.get(pqry.TYPE, ''),
        pqry.USER: _current_user(),
    }
    if new_project[pqry.TYPE] == pqry.COLLECTION:
        new_project.update({field: field in request.form
                            for field in pqry.REQUIREMENT_FIELDS})
    try:
        code = pqry.add(new_project)
    except ValueError as err:
        # add() raises ValueError for a blank name or unknown type.
        flash(str(err), 'error')
        # Back to the list so a page refresh doesn't submit the form again.
        return redirect(url_for('web.project_list'))
    # Adding authors is the next step, so go straight to that part of
    # the new project's page.
    flash(f'Created "{new_project[pqry.NAME]}". Now add its authors.',
          'success')
    return redirect(url_for('web.project_edit', code=code,
                            _anchor=AUTHORS_FIELD))


@web.get('/projects/<code>/edit')
def project_edit(code):
    """Show the form for renaming a project and editing its authors."""
    project = _project_or_none(code)
    if project is None:
        flash('That project no longer exists.', 'error')
        return redirect(url_for('web.project_list'))
    author_names = [author[people.NAME]
                    for author in pp.fetch_authors(code)]
    return render_template('web/project_edit.html', project=project,
                           type_choices=pqry.get_type_choices(),
                           collection_type=pqry.COLLECTION,
                           author_names=author_names)


def _author_names_from_form():
    """
    Turn the authors box into a list of names: one per line, with blank
    lines skipped.
    """
    text = request.form.get(AUTHORS_FIELD, '')
    return [line.strip() for line in text.splitlines() if line.strip()]


@web.post('/projects/<code>/edit')
def project_update(code):
    """Save changes from the edit form, including the list of authors."""
    if _project_or_none(code) is None:
        flash('That project no longer exists.', 'error')
        return redirect(url_for('web.project_list'))
    changes = {pqry.NAME: request.form.get(pqry.NAME, '').strip()}
    if pqry.TYPE in request.form:
        changes[pqry.TYPE] = request.form[pqry.TYPE]
    author_names = _author_names_from_form()
    try:
        # Check the author names first, so a bad name saves nothing.
        for name in author_names:
            people.check_name(name)
        pqry.update(code, changes)
        pp.set_authors(code, author_names)
    except ValueError as err:
        # Stay on the edit page so the person can fix the problem.
        flash(str(err), 'error')
        return redirect(url_for('web.project_edit', code=code))
    flash(f'Saved "{changes[pqry.NAME]}".', 'success')
    return redirect(url_for('web.project_list'))


@web.post('/projects/<code>/delete')
def project_delete(code):
    """
    Delete a project's record. The project's files on disk are kept,
    same as the API's delete, so nobody's manuscripts are lost.
    """
    project = _project_or_none(code)
    if project is None:
        flash('That project was already deleted.', 'error')
    else:
        pqry.delete(code)
        flash(f'Deleted "{project[pqry.NAME]}".', 'success')
    return redirect(url_for('web.project_list'))


# --- Screens for filling in a volume's table of contents and each
# --- author's bio, address and other pieces

def _form_text(field):
    """Browsers send line breaks as CRLF; we keep plain newlines."""
    text = request.form.get(field, '')
    return text.replace('\r\n', '\n').replace('\r', '\n')


def _edited_volume(code):
    """
    Returns the project if it exists and is an edited volume. Otherwise
    flashes why and returns None, so the caller can redirect.
    """
    project = _project_or_none(code)
    if project is None:
        flash('That project no longer exists.', 'error')
        return None
    if project[pqry.TYPE] != pqry.COLLECTION:
        flash('Materials screens are only for edited volumes.', 'error')
        return None
    return project


def _author_or_none(code, person_id):
    """The author on this project with this id, or None."""
    for person in pp.fetch_authors(code):
        if person[people.ID] == person_id:
            return person
    return None


def _piece_rows(project, record):
    """One row per piece: its label, whether it is required and received."""
    rows = []
    for piece, (_, flag) in contributors.PIECES.items():
        field = REQUIRED_BY.get(piece)
        rows.append({'type': piece,
                     'label': PIECE_LABELS.get(piece, piece),
                     'received': bool(record.get(flag)),
                     'required': bool(field and project.get(field))})
    return rows


@web.get('/projects/<code>/materials')
def project_materials(code):
    """The table of contents, and what each author has provided so far."""
    project = _edited_volume(code)
    if project is None:
        return redirect(url_for('web.project_list'))
    by_person = contributors.fetch_by_person(code)
    authors = [{'person': person,
                'pieces': _piece_rows(project,
                                      by_person.get(person[people.ID], {}))}
               for person in pp.fetch_authors(code)]
    return render_template('web/project_materials.html', project=project,
                           toc=project.get('toc') or '', authors=authors,
                           max_toc=MAX_TOC_CHARS)


@web.post('/projects/<code>/toc')
def project_toc_save(code):
    """Save the table of contents. The contributor editor shows the same."""
    if _edited_volume(code) is None:
        return redirect(url_for('web.project_list'))
    here = url_for('web.project_materials', code=code)
    text = _form_text('toc')
    if len(text) > MAX_TOC_CHARS:
        flash('The table of contents must be at most 100,000 characters.',
              'error')
        return redirect(here)
    try:
        saved = pqry.update(code, {'toc': text})
    except ValueError as err:
        flash(str(err), 'error')
        return redirect(here)
    if not saved:
        flash('Could not save the table of contents. Please try again.',
              'error')
        return redirect(here)
    flash('Saved the table of contents.', 'success')
    return redirect(here)


def _fill_in_target(code, person_id, piece):
    """
    Checks the project, author and piece named in a fill-in URL.
    Returns (project, person, None) when all are fine, or
    (None, None, response) with a redirect after flashing the problem.
    """
    if piece not in contributors.PIECES:
        abort(404)
    project = _edited_volume(code)
    if project is None:
        return None, None, redirect(url_for('web.project_list'))
    person = _author_or_none(code, person_id)
    if person is None:
        flash('That person is not an author on this project.', 'error')
        return None, None, redirect(url_for('web.project_materials',
                                            code=code))
    return project, person, None


def _render_piece(project, person, piece, text, status=200):
    return render_template('web/author_piece.html', project=project,
                           person=person, piece=piece,
                           label=PIECE_LABELS.get(piece, piece), text=text,
                           max_text=materials.MAX_TEXT_LENGTH), status


@web.get('/projects/<code>/authors/<person_id>/<piece>')
def author_piece(code, person_id, piece):
    """A text box for one piece (bio, address...) from one author."""
    project, person, problem = _fill_in_target(code, person_id, piece)
    if problem is not None:
        return problem
    record = contributors.fetch_for_person(code, person_id)
    text = (materials.read_text(code, record[contributors.ID], piece)
            if record else '')
    return _render_piece(project, person, piece, text)


@web.post('/projects/<code>/authors/<person_id>/<piece>')
def author_piece_save(code, person_id, piece):
    """Save the piece. Whatever was typed stays in the box after an error."""
    project, person, problem = _fill_in_target(code, person_id, piece)
    if problem is not None:
        return problem
    text = _form_text('text')
    try:
        record = contributors.ensure_for_person(code, person_id,
                                                person[people.NAME])
        materials.save_text(code, record[contributors.ID], piece, text)
    except ValueError as err:
        flash(str(err), 'error')
        return _render_piece(project, person, piece, text, 400)
    except (KeyError, OSError) as err:
        current_app.logger.error('Could not save %s: %s', piece, err)
        flash('Could not save. Please try again.', 'error')
        return _render_piece(project, person, piece, text, 500)
    label = PIECE_LABELS.get(piece, piece).lower()
    flash(f'Saved {label} for {person[people.NAME]}.', 'success')
    return redirect(url_for('web.project_materials', code=code))

