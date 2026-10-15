"""Keep test project folders separate from real manuscripts."""
import pytest


@pytest.fixture(autouse=True)
def project_files(tmp_path, monkeypatch):
    monkeypatch.setenv('WRITERS_PROJECTS_DIR', str(tmp_path / 'projects'))
