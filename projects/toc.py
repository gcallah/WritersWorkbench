"""A volume's table of contents: one uploaded markdown file per project."""
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import RLock

from projects import query, storage


FILE_NAME = 'table_of_contents.md'
EXTENSIONS = {'.md', '.markdown'}
MAX_LENGTH = 100_000
# A UTF-8 character takes at most 4 bytes.
MAX_BYTES = 4 * MAX_LENGTH
_LOCK = RLock()


def _volume(project_code):
    """Return the project, which must exist and be an edited volume."""
    project = query.fetch_by_key(project_code)
    if project is None:
        raise KeyError('Project not found.')
    if not query.is_multi_author(project[query.TYPE]):
        raise ValueError(
            'Table of contents requires an edited-volume '
            'or journal-issue project.')
    return project


def _write(path, text):
    temporary = None
    try:
        with NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def read(project_code):
    """Return the saved markdown, or an empty string if there is none."""
    with _LOCK:
        _volume(project_code)
        path = storage.project_directory(project_code) / FILE_NAME
        return path.read_text(encoding='utf-8') if path.exists() else ''


def save(project_code, text):
    """Replace the table of contents file with this text; return it."""
    if not isinstance(text, str):
        raise ValueError('The table of contents must be text.')
    if not text.strip():
        raise ValueError('The table of contents is empty.')
    if len(text) > MAX_LENGTH:
        raise ValueError(
            'Table of contents must be at most 100,000 characters.')
    with _LOCK:
        _volume(project_code)
        directory = storage.prepare_project(project_code)
        _write(directory / FILE_NAME, text)
    return text


def save_file(project_code, data):
    """Save an uploaded markdown file's bytes; return the text saved.

    The upload's own file name is never used to build a path."""
    if not isinstance(data, bytes) or not data:
        raise ValueError('Choose a markdown (.md) file that is not empty.')
    if len(data) > MAX_BYTES:
        raise ValueError(
            'The file is too large. Use at most 100,000 characters.')
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ValueError('The file must be UTF-8 text.') from None
    return save(project_code, text.replace('\r\n', '\n').replace('\r', '\n'))
