"""Files and receipt flags follow the same project and author."""
from unittest.mock import patch

import pytest
from backendcore.data.caching import get_cache

from projects import materials, people, query, storage
import projects.person_project as pp


@pytest.fixture
def author():
    code = query.add({**query.TEST_SAMPLE, query.TYPE: query.COLLECTION})
    person = people.add('Ada Writer', [people.AUTHOR])
    pp.link(person, code, people.AUTHOR)
    yield code, person
    people.delete(person)
    query.delete(code)


@pytest.mark.parametrize('piece', pp.PIECES)
def test_material_saved_in_category_and_only_its_flag_set(author, piece):
    code, person = author
    text = 'Renée writes.\nSecond line.'
    record = materials.save_text(code, person, piece, text)
    folder, flag = pp.PIECES[piece]
    assert (storage.project_directory(code) / folder
            / f'{person}.txt').read_text() == text
    assert record[flag] is True
    flags = [value[1] for value in pp.PIECES.values()]
    assert all(record[other] is False for other in flags if other != flag)
    get_cache(pp.COLLECT).clear_cache()
    assert pp.fetch_author_status(code, person)[flag] is True
    assert materials.read_text(code, person, piece) == text


def test_binary_permission_and_text_replacement(author):
    code, person = author
    data = b'%PDF-1.4\nexample bytes\x00\xff'
    materials.save_file(code, person, 'permission', data, '.pdf')
    path = materials.piece_path(code, person, 'permission', '.pdf')
    assert path.read_bytes() == data
    materials.save_text(code, person, 'bio', 'Old')
    materials.save_text(code, person, 'bio', 'New')
    assert materials.read_text(code, person, 'bio') == 'New'


def test_failed_write_does_not_mark_received(author):
    code, person = author
    with patch.object(materials, '_write', side_effect=OSError('Disk full')):
        with pytest.raises(OSError):
            materials.save_text(code, person, 'bio', 'Biography')
    assert not pp.fetch_author_status(code, person)['Bio']
    assert materials.read_text(code, person, 'bio') == ''


def test_database_failure_is_reported_and_save_can_be_retried(author):
    code, person = author
    with patch.object(pp, 'mark_received', side_effect=OSError):
        with pytest.raises(OSError):
            materials.save_text(code, person, 'bio', 'Biography')
    assert not pp.fetch_author_status(code, person)['Bio']
    assert materials.save_text(code, person, 'bio', 'Biography')['Bio']


@pytest.mark.parametrize('piece,extension', [
    ('../../outside', '.txt'), ('bio', '/../../../outside'),
    ('bio', '.exe'),
])
def test_unsafe_paths(author, piece, extension):
    with pytest.raises(ValueError):
        materials.save_file(*author, piece, b'text', extension)


def test_wrong_project_cannot_write(author):
    other = query.add({**query.TEST_SAMPLE, query.TYPE: query.COLLECTION})
    try:
        with pytest.raises(KeyError):
            materials.save_text(other, author[1], 'bio', 'Wrong book')
        assert not (storage.project_directory(other) / 'bios').exists()
    finally:
        query.delete(other)


@pytest.mark.parametrize('text', [None, '', '  ', 42, 'a' * 100_001])
def test_invalid_text(author, text):
    with pytest.raises(ValueError):
        materials.save_text(*author, 'bio', text)
