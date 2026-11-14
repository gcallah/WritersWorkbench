"""Project creation provisions a safe, repeatable book layout."""
import pytest

from projects import query, storage


def test_collection_creation_and_rename():
    code = query.add({**query.TEST_SAMPLE, query.TYPE: query.COLLECTION,
                      'requires_keywords': True})
    try:
        directory = storage.project_directory(code)
        assert {p.name for p in directory.iterdir()} == {
            'chapters', 'drafts', 'Proposal', 'keywords'}
        manuscript = directory / 'chapters' / 'draft.txt'
        manuscript.write_text('Keep this draft')
        query.update(code, {query.NAME: 'New title', 'requires_abstract': True,
                            'requires_keywords': False})
        assert (directory / 'abstracts').is_dir()
        assert (directory / 'keywords').is_dir()
        assert not (directory / 'bios').exists()
        assert manuscript.read_text() == 'Keep this draft'
    finally:
        query.delete(code)
    # Removing the DB record must not silently erase manuscripts.
    assert manuscript.read_text() == 'Keep this draft'


def test_rejected_conversion_leaves_directory_untouched():
    code = query.add(query.TEST_SAMPLE)
    try:
        directory = storage.project_directory(code)
        assert directory.is_dir()
        assert not list(directory.iterdir())
        with pytest.raises(ValueError, match='type cannot change'):
            query.update(code, {query.TYPE: query.COLLECTION})
        assert not list(directory.iterdir())
    finally:
        query.delete(code)


@pytest.mark.parametrize('code', ['../outside', '/tmp/book', '', None])
def test_unsafe_project_code(code):
    with pytest.raises(ValueError):
        storage.prepare_project(code, True)


def test_failed_folder_creation_does_not_add_project(monkeypatch):
    before = query.fetch_codes()

    def fail(*args):
        raise OSError('Cannot create directory')

    monkeypatch.setattr(query, 'prepare_project', fail)
    with pytest.raises(OSError):
        query.add(query.TEST_SAMPLE)
    assert query.fetch_codes() == before
