"""Project directories modeled on gcallah/JustifyingTheState."""
import os
from pathlib import Path
import re


# Core working folders belong to every edited volume. Author submissions
# get their own folders only when requested or actually received.
CORE_FOLDERS = ('chapters', 'drafts', 'Proposal')
AUTHOR_COMPONENTS = {
    'requires_bio': ('A biography', 'bios'),
    'requires_permission': ('Permission to publish', 'permissions'),
    'requires_address': ('An address', 'addresses'),
    'requires_abstract': ('An abstract', 'abstracts'),
    'requires_keywords': ('Keywords', 'keywords'),
}


def project_directory(code):
    """Use immutable generated codes, never names supplied by the user."""
    if not isinstance(code, str) or not re.fullmatch(r'[0-9a-f]{32}', code):
        raise ValueError('Invalid project code.')
    default = Path(__file__).resolve().parents[1] / 'instance' / 'projects'
    return Path(os.getenv('WRITERS_PROJECTS_DIR', str(default))) / code


def prepare_project(code, edited_volume=False, requirements=None):
    """Create missing folders without modifying existing manuscripts."""
    directory = project_directory(code)
    directory.mkdir(parents=True, exist_ok=True)
    if edited_volume:
        selected = requirements or {}
        folders = [folder for field, (_, folder) in AUTHOR_COMPONENTS.items()
                   if selected.get(field)]
        for name in (*CORE_FOLDERS, *folders):
            (directory / name).mkdir(exist_ok=True)
    return directory
