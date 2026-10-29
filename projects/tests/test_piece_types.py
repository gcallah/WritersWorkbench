"""Every editor text box (issue #18) saves to its own folder and flag."""
import pytest
from backendcore.data.caching import get_cache

from projects import contributors, materials, query, storage

PIECES = ['bio', 'submission', 'abstract', 'address', 'keywords',
          'permission', 'referee_report']


@pytest.fixture
def author():
    code = query.add({**query.TEST_SAMPLE, query.TYPE: query.COLLECTION})
    record = contributors.add(code, 'Ada Writer')
    yield code, record['id']
    get_cache(contributors.COLLECT).delete(record['id'])
    query.delete(code)


def test_editor_pieces_are_all_supported():
    assert set(PIECES) <= set(contributors.PIECES)


def test_referee_report_has_own_folder_and_flag():
    folder, flag = contributors.PIECES['referee_report']
    assert folder == 'referee_reports'
    assert flag == 'RefereeReport'
    assert folder in storage.VOLUME_FOLDERS


@pytest.mark.parametrize('piece', PIECES)
def test_pasted_text_round_trips_and_sets_only_its_flag(author, piece):
    code, person = author
    pasted = f'Pasted {piece} text.\nSecond line.'
    record = materials.save_text(code, person, piece, pasted)
    flag = contributors.PIECES[piece][1]
    assert record[flag] is True
    others = [f for _, f in contributors.PIECES.values() if f != flag]
    assert all(not record[other] for other in others)
    assert materials.read_text(code, person, piece) == pasted


def test_pieces_for_one_contributor_do_not_overwrite_each_other(author):
    code, person = author
    materials.save_text(code, person, 'address', '1 Main Street')
    materials.save_text(code, person, 'referee_report', 'Accept.')
    assert materials.read_text(code, person, 'address') == '1 Main Street'
    assert materials.read_text(code, person, 'referee_report') == 'Accept.'


def test_referee_report_works_for_older_volume_without_its_folder(author):
    code, person = author
    folder = storage.project_directory(code) / 'referee_reports'
    if folder.exists():
        folder.rmdir()
    materials.save_text(code, person, 'referee_report', 'Late report')
    assert materials.read_text(code, person, 'referee_report') == 'Late report'
