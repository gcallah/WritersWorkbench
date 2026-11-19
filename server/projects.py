"""Contributor records and text pieces stored in the workbench directory."""
import json
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import RLock
from datetime import datetime, timezone
from uuid import uuid4

from projects import contributors, materials, people, storage
import projects.person_project as pp


PIECE_TYPES = {'bio': 'Bio', 'submission': 'Submission'}
MAX_TEXT_LENGTH = 100_000
MAX_COMMENT_LENGTH = 5_000
_LOCK = RLock()


def _new_comment(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Enter a comment before posting.')
    if len(text) > MAX_COMMENT_LENGTH:
        raise ValueError('Comments must be at most 5,000 characters.')
    return {
        'id': uuid4().hex,
        'author': 'Editor',
        'text': text.strip(),
        'created_at': datetime.now(timezone.utc).isoformat(),
    }


def _read_comments(path):
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding='utf-8'))


def _append_comment(path, text):
    comment = _new_comment(text)
    comments = _read_comments(path)
    comments.append(comment)
    path.parent.mkdir(parents=True, exist_ok=True)
    ContributorStore._write(path, json.dumps(comments, ensure_ascii=False))
    return comment


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
        for record in records:
            record.setdefault('HasReferee', None)
        return sorted(records, key=lambda record: record['name'].casefold())

    def add_contributor(self, name):
        """Create a contributor without accepting a filesystem path."""
        if not isinstance(name, str) or not name.strip() or len(name) > 200:
            raise ValueError(
                'Enter a contributor name of 1 to 200 characters.')
        record = {'id': uuid4().hex, 'name': name.strip(),
                  'Bio': False, 'Submission': False, 'HasReferee': None}
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

    def get_comments(self, contributor_id, piece_type):
        if piece_type not in PIECE_TYPES:
            raise ValueError('Unknown piece type.')
        with _LOCK:
            directory = self._directory(contributor_id)
            return _read_comments(
                directory / 'comments' / f'{piece_type}.json')

    def add_comment(self, contributor_id, piece_type, text):
        if piece_type not in PIECE_TYPES:
            raise ValueError('Unknown piece type.')
        with _LOCK:
            directory = self._directory(contributor_id)
            return _append_comment(
                directory / 'comments' / f'{piece_type}.json', text)

    def save_file(self, contributor_id, piece_type, data, extension):
        """Save an uploaded document, then mark its piece received."""
        if piece_type not in PIECE_TYPES:
            raise ValueError('Unknown piece type.')
        if (extension not in {'.docx', '.pdf'} or not isinstance(data, bytes)
                or not data or len(data) > materials.MAX_FILE_BYTES):
            raise ValueError('Provide a Word or PDF file of at most 10 MB.')
        with _LOCK:
            directory = self._directory(contributor_id)
            record_path = directory / 'contributor.json'
            record = json.loads(record_path.read_text(encoding='utf-8'))
            self._write_bytes(directory / f'{piece_type}{extension}', data)
            record[PIECE_TYPES[piece_type]] = True
            self._write(record_path, json.dumps(record))
        return record

    def set_referee(self, contributor_id, has_referee):
        """Save whether the contributor's paper has a referee."""
        if type(has_referee) is not bool:
            raise ValueError('Referee answer must be true or false.')
        with _LOCK:
            directory = self._directory(contributor_id)
            record_path = directory / 'contributor.json'
            record = json.loads(record_path.read_text(encoding='utf-8'))
            record['HasReferee'] = has_referee
            self._write(record_path, json.dumps(record))
        return record

    @staticmethod
    def _write_bytes(path, data):
        temporary = None
        try:
            with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(data)
            temporary.replace(path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


class ProjectContributorStore:
    """
    The editor's contributors for one book are the book's authors, from
    the People and person_project tables (issue #34).
    """

    def __init__(self, project_code):
        contributors.require_volume(project_code)
        self.project_code = project_code

    def _record(self, person):
        """What the editor shows for one author: name and piece status."""
        return {'id': person[people.ID], 'name': person[people.NAME],
                **pp.fetch_author_status(self.project_code,
                                         person[people.ID])}

    def _fetch(self, person_id):
        """This author's record; KeyError if they aren't on this book."""
        person = people.fetch_by_key(person_id)
        if person is None:
            raise KeyError('Contributor not found in this project.')
        return self._record(person)

    def list_contributors(self):
        return [self._record(person)
                for person in pp.fetch_authors(self.project_code)]

    def add_contributor(self, name):
        """Add an author by name, reusing a person who has that name."""
        found = people.fetch_by_name(name)
        person_id = (next(iter(found)) if found
                     else people.add(name, [people.AUTHOR]))
        pp.link(person_id, self.project_code, people.AUTHOR)
        return self._fetch(person_id)

    def get_piece(self, contributor_id, piece_type):
        return materials.read_text(self.project_code, contributor_id,
                                   piece_type)

    def save_piece(self, contributor_id, piece_type, text):
        materials.save_text(self.project_code, contributor_id,
                            piece_type, text)
        return self._fetch(contributor_id)

    def _comments_path(self, contributor_id, piece_type):
        if piece_type not in pp.PIECES:
            raise ValueError('Unknown piece type.')
        self._fetch(contributor_id)
        return (storage.project_directory(self.project_code) / 'comments'
                / contributor_id / f'{piece_type}.json')

    def get_comments(self, contributor_id, piece_type):
        with _LOCK:
            return _read_comments(
                self._comments_path(contributor_id, piece_type))

    def add_comment(self, contributor_id, piece_type, text):
        with _LOCK:
            return _append_comment(
                self._comments_path(contributor_id, piece_type), text)

    def save_file(self, contributor_id, piece_type, data, extension):
        materials.save_file(self.project_code, contributor_id,
                            piece_type, data, extension)
        return self._fetch(contributor_id)

    def set_referee(self, contributor_id, has_referee):
        pp.set_referee(self.project_code, contributor_id, has_referee)
        return self._fetch(contributor_id)
