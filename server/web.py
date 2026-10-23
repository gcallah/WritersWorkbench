"""
A simple web interface for the Writer's Workbench (issue #4).

Before this, projects could only be managed through the JSON API or by
running Python code. These pages let someone do the same things from a
browser: see all projects, create one, rename it or change its type, and
delete it.

The pages live under /web so they don't collide with the API's Swagger
page, which already uses "/".
"""
from secrets import compare_digest

from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, url_for)

import projects.query as pqry


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
    return render_template('web/projects.html',
                           projects=all_projects,
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
    try:
        pqry.add(new_project)
        flash(f'Created "{new_project[pqry.NAME]}".', 'success')
    except ValueError as err:
        # add() raises ValueError for a blank name or unknown type.
        flash(str(err), 'error')
    # Send the browser back to the list so a page refresh doesn't
    # submit the form a second time.
    return redirect(url_for('web.project_list'))


@web.get('/projects/<code>/edit')
def project_edit(code):
    """Show the form for renaming a project or changing its type."""
    project = _project_or_none(code)
    if project is None:
        flash('That project no longer exists.', 'error')
        return redirect(url_for('web.project_list'))
    return render_template('web/project_edit.html', project=project,
                           type_choices=pqry.get_type_choices())


@web.post('/projects/<code>/edit')
def project_update(code):
    """Save changes from the edit form."""
    if _project_or_none(code) is None:
        flash('That project no longer exists.', 'error')
        return redirect(url_for('web.project_list'))
    changes = {
        pqry.NAME: request.form.get(pqry.NAME, '').strip(),
        pqry.TYPE: request.form.get(pqry.TYPE, ''),
    }
    try:
        pqry.update(code, changes)
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
