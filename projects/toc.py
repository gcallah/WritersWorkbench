"""
A volume's table of contents: one markdown file per project.

The editor uploads a markdown (.md) or Word (.docx) file. A Word file is
converted to markdown, so what is stored is always table_of_contents.md.
"""
import io
import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import RLock

import mammoth

from projects import query, storage


FILE_NAME = 'table_of_contents.md'
MARKDOWN_EXTENSIONS = {'.md', '.markdown'}
WORD_EXTENSION = '.docx'
EXTENSIONS = MARKDOWN_EXTENSIONS | {WORD_EXTENSION}
MAX_LENGTH = 100_000
# A UTF-8 character takes at most 4 bytes.
MAX_BYTES = 4 * MAX_LENGTH
# A Word file is a zip, so it is bigger than its text; same cap as pieces.
MAX_WORD_BYTES = 10_000_000
# Largest we let a Word file expand to, as a guard against zip bombs.
MAX_WORD_UNPACKED = 100_000_000
# What the upload endpoints read at most (one byte over, to spot too big).
MAX_UPLOAD_BYTES = MAX_WORD_BYTES
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


def _word_to_markdown(data):
    """Convert the bytes of a .docx file to markdown text."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            unpacked = sum(item.file_size for item in archive.infolist())
        if unpacked > MAX_WORD_UNPACKED:
            raise ValueError('That Word file is too large.')
        result = mammoth.convert_to_markdown(io.BytesIO(data))
    except ValueError:
        raise
    except Exception:  # not a zip, or not a real Word file
        raise ValueError('Could not read that Word file. Save it as a '
                         '.docx document and try again.') from None
    return result.value.replace('\r\n', '\n').replace('\r', '\n').strip()


def save_word(project_code, data):
    """Convert an uploaded .docx file to markdown and save it as the
    table of contents; return the text saved."""
    if not isinstance(data, bytes) or not data:
        raise ValueError('Choose a Word (.docx) file that is not empty.')
    if len(data) > MAX_WORD_BYTES:
        raise ValueError('The Word file must be at most 10 MB.')
    text = _word_to_markdown(data)
    if not text:
        raise ValueError('That Word file has no text to use.')
    return save(project_code, text)


def save_upload(project_code, filename, data):
    """Save an uploaded .md, .markdown or .docx file; return the text.

    Only the file name's extension is used, never to build a path."""
    suffix = Path(filename or '').suffix.lower()
    if suffix == WORD_EXTENSION:
        return save_word(project_code, data)
    if suffix in MARKDOWN_EXTENSIONS:
        return save_file(project_code, data)
    raise ValueError('Choose a .md, .markdown or .docx file.')
