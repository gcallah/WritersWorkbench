"""A volume's table of contents is one uploaded markdown file."""
from unittest.mock import patch

import pytest

from projects import query, storage, toc


@pytest.fixture
def volume():
    code = query.add({**query.TEST_SAMPLE, query.TYPE: query.COLLECTION})
    yield code
    query.delete(code)


def test_empty_until_uploaded(volume):
    assert toc.read(volume) == ''


def test_upload_is_saved_as_a_markdown_file(volume):
    text = '# Contents\n\n1. Introduction\n2. Renée on method\n'
    assert toc.save_file(volume, text.encode('utf-8')) == text
    path = storage.project_directory(volume) / toc.FILE_NAME
    assert path.read_text(encoding='utf-8') == text
    assert toc.read(volume) == text


def test_upload_replaces_and_leaves_no_temporary_files(volume):
    toc.save_file(volume, b'# Old')
    toc.save_file(volume, b'# New')
    assert toc.read(volume) == '# New'
    files = [p.name for p in storage.project_directory(volume).iterdir()
             if p.is_file()]
    assert files == [toc.FILE_NAME]


def test_byte_order_mark_and_windows_line_endings(volume):
    toc.save_file(volume, b'\xef\xbb\xbf# Contents\r\n\r\n1. Intro\r\n')
    assert toc.read(volume) == '# Contents\n\n1. Intro\n'


def test_volumes_have_separate_tables_of_contents(volume):
    other = query.add({**query.TEST_SAMPLE, query.TYPE: query.COLLECTION})
    try:
        toc.save_file(volume, b'First book')
        toc.save_file(other, b'Second book')
        assert toc.read(volume) == 'First book'
        assert toc.read(other) == 'Second book'
    finally:
        query.delete(other)


def test_only_edited_volumes_have_one():
    code = query.add(query.TEST_SAMPLE)
    try:
        with pytest.raises(ValueError):
            toc.save_file(code, b'# A solo book')
        with pytest.raises(ValueError):
            toc.read(code)
    finally:
        query.delete(code)


@pytest.mark.parametrize('data', [
    b'', b'   \n', 'not bytes', None, 42, b'\xff\xfe\x00bad',
    b'a' * (toc.MAX_LENGTH + 1), b'a' * (toc.MAX_BYTES + 1),
])
def test_invalid_uploads_change_nothing(volume, data):
    toc.save_file(volume, b'Keep me')
    with pytest.raises(ValueError):
        toc.save_file(volume, data)
    assert toc.read(volume) == 'Keep me'


@pytest.mark.parametrize('text', [None, 42, True, ['a'], {'a': 1}, '',
                                  '  \n', 'a' * (toc.MAX_LENGTH + 1)])
def test_save_rejects_anything_but_real_text(volume, text):
    toc.save(volume, 'Keep me')
    with pytest.raises(ValueError):
        toc.save(volume, text)
    assert toc.read(volume) == 'Keep me'


def test_missing_project():
    with pytest.raises(KeyError):
        toc.read('missing')
    with pytest.raises(KeyError):
        toc.save_file('missing', b'text')


def test_failed_write_keeps_old_text(volume):
    toc.save_file(volume, b'Old')
    with patch.object(toc, '_write', side_effect=OSError('Disk full')):
        with pytest.raises(OSError):
            toc.save_file(volume, b'New')
    assert toc.read(volume) == 'Old'
