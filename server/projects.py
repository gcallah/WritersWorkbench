"""Contributor records and text pieces stored in the workbench directory."""
import json
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import RLock
from uuid import uuid4

from projects import contributors, materials


PIECE_TYPES = {'bio': 'Bio', 'submission': 'Submission'}
MAX_TEXT_LENGTH = 100_000
_LOCK = RLock()


class ContributorStore:
    """Keep each contributor's record and pieces in their own directory."""

    def __init__(self, root):
        self.root = Path(root)

    def _directory(self, contributor_id):
        if not re.fullmatch(r'[0-9a-f]{32}', contributor_id):
            raise ValueError('Invalid contributor ID.')
        directory = self.root / contributor_id
        if not (directory / 'contributor.json').is_file():
            raise KeyError(contributor_id)
        return directory

    @staticmethod
    def _write(path, text):
        temporary = None
        try:
            with NamedTemporaryFile(mode='w', encoding='utf-8',
                                    dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(text)
            temporary.replace(path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def list_contributors(self):
        """Return contributor records sorted by display name."""
        with _LOCK:
            records = [json.loads(path.read_text(encoding='utf-8'))
                       for path in self.root.glob('*/contributor.json')]
        return sorted(records, key=lambda record: record['name'].casefold())

    def add_contributor(self, name):
        """Create a contributor without accepting a filesystem path."""
        if not isinstance(name, str) or not name.strip() or len(name) > 200:
            raise ValueError(
                'Enter a contributor name of 1 to 200 characters.')
        record = {'id': uuid4().hex, 'name': name.strip(),
                  'Bio': False, 'Submission': False}
        with _LOCK:
            directory = self.root / record['id']
            directory.mkdir(parents=True)
            self._write(directory / 'contributor.json', json.dumps(record))
        return record

    def get_piece(self, contributor_id, piece_type):
        """Return an existing piece, or an empty draft."""
        if piece_type not in PIECE_TYPES:
            raise ValueError('Unknown piece type.')
        with _LOCK:
            directory = self._directory(contributor_id)
            path = directory / f'{piece_type}.txt'
            return path.read_text(encoding='utf-8') if path.exists() else ''

    def save_piece(self, contributor_id, piece_type, text):
        """Save text before marking the contributor field true."""
        if piece_type not in PIECE_TYPES:
            raise ValueError('Unknown piece type.')
        if not isinstance(text, str) or not text.strip():
            raise ValueError('Enter some text before saving.')
        if len(text) > MAX_TEXT_LENGTH:
            raise ValueError('Pieces must be at most 100,000 characters.')
        with _LOCK:
            directory = self._directory(contributor_id)
            record_path = directory / 'contributor.json'
            record = json.loads(record_path.read_text(encoding='utf-8'))
            self._write(directory / f'{piece_type}.txt', text)
            record[PIECE_TYPES[piece_type]] = True
            self._write(record_path, json.dumps(record))
        return record


class ProjectContributorStore:
    """Use the same editor interface for contributors belonging to a book."""

    def __init__(self, project_code):
        contributors.require_volume(project_code)
        self.project_code = project_code

    def list_contributors(self):
        return contributors.fetch_list(self.project_code)

    def add_contributor(self, name):
        return contributors.add(self.project_code, name)

    def get_piece(self, contributor_id, piece_type):
        return materials.read_text(self.project_code, contributor_id,
                                   piece_type)

    def save_piece(self, contributor_id, piece_type, text):
        return materials.save_text(self.project_code, contributor_id,
                                   piece_type, text)
