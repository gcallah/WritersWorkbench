"""Save contributor materials in the edited volume's category folders."""
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import RLock

from projects import contributors, storage


MAX_TEXT_LENGTH = 100_000
MAX_FILE_BYTES = 10_000_000
_LOCK = RLock()
EXTENSIONS = {'.txt', '.md', '.docx', '.pdf'}


def piece_path(project_code, contributor_id, piece_type, extension='.txt'):
    """Validate membership before constructing any path."""
    contributors.fetch(project_code, contributor_id)
    if piece_type not in contributors.PIECES:
        raise ValueError('Unknown piece type.')
    if extension not in EXTENSIONS:
        raise ValueError('Use .txt, .md, .docx, or .pdf files.')
    folder = contributors.PIECES[piece_type][0]
    return (storage.project_directory(project_code) / folder
            / f'{contributor_id}{extension}')


def _write(path, data):
    temporary = None
    try:
        with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def save_file(project_code, contributor_id, piece_type, data,
              extension='.txt'):
    """Save bytes first, then mark receipt in the DB; never execute files."""
    if not isinstance(data, bytes) or not data or len(data) > MAX_FILE_BYTES:
        raise ValueError('Provide a nonempty file of at most 10 MB.')
    with _LOCK:
        path = piece_path(project_code, contributor_id, piece_type, extension)
        storage.prepare_project(project_code, edited_volume=True)
        _write(path, data)
        return contributors.mark_received(
            project_code, contributor_id, piece_type)


def save_text(project_code, contributor_id, piece_type, text):
    """Adapter for the existing editor's plain-text fields."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Enter some text before saving.')
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError('Pieces must be at most 100,000 characters.')
    return save_file(project_code, contributor_id, piece_type,
                     text.encode('utf-8'))


def read_text(project_code, contributor_id, piece_type):
    """Return the plain-text version, or an empty draft if none exists."""
    with _LOCK:
        path = piece_path(project_code, contributor_id, piece_type)
        return path.read_text(encoding='utf-8') if path.exists() else ''
