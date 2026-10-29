"""Project directories modeled on gcallah/JustifyingTheState."""
import os
from pathlib import Path
import re


VOLUME_FOLDERS = (
    'abstracts', 'addresses', 'bios', 'chapters', 'keywords',
    'permissions', 'referee_reports', 'drafts', 'Proposal',
)


def project_directory(code):
    """Use immutable generated codes, never names supplied by the user."""
    if not isinstance(code, str) or not re.fullmatch(r'[0-9a-f]{32}', code):
        raise ValueError('Invalid project code.')
    default = Path(__file__).resolve().parents[1] / 'instance' / 'projects'
    return Path(os.getenv('WRITERS_PROJECTS_DIR', str(default))) / code


def prepare_project(code, edited_volume=False):
    """Create missing folders without modifying existing manuscripts."""
    directory = project_directory(code)
    directory.mkdir(parents=True, exist_ok=True)
    if edited_volume:
        for name in VOLUME_FOLDERS:
            (directory / name).mkdir(exist_ok=True)
    return directory
