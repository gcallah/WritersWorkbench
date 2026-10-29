'use strict';

const byId = (id) => document.getElementById(id);
const text = byId('piece-text');
const tabs = [...document.querySelectorAll('[data-type]')];
const labels = {
  bio: 'Biography', submission: 'Submission', abstract: 'Abstract',
  address: 'Address', keywords: 'Keywords', permission: 'Permission',
  referee_report: 'Referee report',
};
const flags = {
  bio: 'Bio', submission: 'Submission', abstract: 'Abstract',
  address: 'Address', keywords: 'Keywords', permission: 'Permission',
  referee_report: 'RefereeReport',
};
const placeholders = {
  bio: 'Paste the contributor\'s biography here.',
  submission: 'Paste the chapter or paper text here.',
  abstract: 'Paste the abstract here.',
  address: 'Paste the contributor\'s mailing address here.',
  keywords: 'Paste the keywords here.',
  permission: 'Paste the permission-to-publish statement here.',
  referee_report: 'Paste the referee report here.',
};
// These pieces need a project folder, so they are hidden for unassigned contributors.
const visibleTabs = () => tabs.filter((tab) => !tab.hidden);
let contributors = [];
let selected = null;
let pieceType = 'bio';
let savedText = '';
let busy = false;
let creating = false;
let projectCode = '';
let projectsAvailable = false;
const requirementFields = ['requires_bio', 'requires_permission', 'requires_address'];
let savedRequirements = null;

function requirementValues() {
  return Object.fromEntries(requirementFields.map((field) => [field, byId(field).checked]));
}

function requirementsDirty() {
  return savedRequirements !== null && requirementFields.some(
    (field) => byId(field).checked !== savedRequirements[field]);
}

function requirementsStatus(message, error = false) {
  byId('requirements-status').textContent = message;
  byId('requirements-status').classList.toggle('error', error);
}

async function loadRequirements() {
  savedRequirements = null;
  requirementFields.forEach((field) => { byId(field).checked = false; });
  requirementsStatus('');
  updateControls();
  if (!projectCode) return;
  requirementsStatus('Loading requirements...');
  try {
    const data = await api(`/api/editor/projects/${encodeURIComponent(projectCode)}/requirements`);
    savedRequirements = data.requirements;
    requirementFields.forEach((field) => { byId(field).checked = savedRequirements[field]; });
    requirementsStatus('Requirements loaded.');
  } catch (error) {
    requirementsStatus(`Could not load requirements: ${error.message} Select the project again to retry.`, true);
  }
}


async function api(path, options = {}) {
  const url = new URL(path, location.origin);
  if (projectCode && path.startsWith('/api/contributors')) {
    url.searchParams.set('project', projectCode);
  }
  const response = await fetch(url, { credentials: 'same-origin', ...options });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'The request failed.');
  return data;
}

function status(message, error = false) {
  byId('save-status').textContent = message;
  byId('save-status').classList.toggle('error', error);
}

function pieceDirty() {
  return selected !== null && text.value !== savedText;
}

function refereeAnswer() {
  const value = byId('has-referee').value;
  return value === 'yes' ? true : value === 'no' ? false : null;
}

function refereeDirty() {
  return selected !== null && pieceType === 'submission' &&
    refereeAnswer() !== (selected.HasReferee ?? null);
}

function documentPending() {
  return byId('document-file').files.length > 0;
}

function dirty() {
  return pieceDirty() || refereeDirty() || documentPending() || requirementsDirty();
}

function allowDiscard(includeRequirements = false) {
  const unsaved = pieceDirty() || refereeDirty() || documentPending() ||
    (includeRequirements && requirementsDirty());
  return !unsaved || confirm('Discard unsaved changes?');
}

function clearDocumentUpload() {
  byId('document-file').value = '';
  byId('file-name').textContent = 'Choose Word or PDF';
}

function updateControls() {
  byId('project-select').disabled = busy || creating || !projectsAvailable;
  text.disabled = busy || selected === null;
  byId('save').disabled = busy || !pieceDirty() || !text.value.trim();
  byId('document-file').disabled = busy || selected === null;
  byId('upload-document').disabled = busy || selected === null || !byId('document-file').files.length;
  byId('referee-form').hidden = selected === null || pieceType !== 'submission';
  byId('has-referee').disabled = busy || selected === null;
  byId('save-referee').disabled = busy || !refereeDirty();
  byId('requirements-form').hidden = !projectCode;
  byId('requirements-fields').disabled = busy || creating || savedRequirements === null;
  byId('requirements-save').disabled = busy || creating || !requirementsDirty();
  byId('add').disabled = busy;
  tabs.forEach((tab) => {
    if ('projectOnly' in tab.dataset) tab.hidden = !projectCode;
    tab.disabled = busy || selected === null;
  });
  byId('character-count').textContent = `${text.value.length.toLocaleString()} / 100,000`;
}

function renderContributors() {
  const list = byId('contributors');
  list.replaceChildren();
  const search = byId('search').value.toLocaleLowerCase();
  const matches = contributors.filter((record) => record.name.toLocaleLowerCase().includes(search));
  byId('count').textContent = contributors.length;
  byId('list-status').textContent = matches.length ? '' :
    (contributors.length ? 'No matching contributors' : 'No contributors yet');
  matches.forEach((record) => {
    const button = document.createElement('button');
    button.className = 'contributor';
    button.setAttribute('aria-current', String(selected?.id === record.id));
    const name = document.createElement('span');
    name.className = 'contributor-name';
    name.textContent = record.name;
    const meta = document.createElement('span');
    meta.className = `contributor-meta${record.Bio ? ' complete' : ''}`;
    meta.textContent = record.Bio ? 'Bio received' : 'Bio pending';
    button.append(name, meta);
    button.addEventListener('click', () => {
      if (!busy && record.id !== selected?.id && allowDiscard()) loadPiece(record, pieceType);
    });
    list.append(button);
  });
}

function renderReceipt() {
  const received = Boolean(selected?.[flags[pieceType]]);
  byId('received').textContent = received ? 'Received' : 'Not received';
  byId('received').classList.toggle('received', received);
}

async function loadPiece(record, type) {
  busy = true;
  clearDocumentUpload();
  updateControls();
  status('Loading...');
  try {
    const data = await api(`/api/contributors/${record.id}/pieces/${type}`);
    selected = record;
    pieceType = type;
    savedText = data.text;
    text.value = savedText;
    byId('has-referee').value = record.HasReferee === true ? 'yes' :
      record.HasReferee === false ? 'no' : '';
    byId('referee-status').textContent = record.HasReferee === null ||
      record.HasReferee === undefined ? 'No answer saved' : 'Answer saved';
    byId('contributor-name').textContent = record.name;
    byId('piece-label').textContent = labels[type];
    text.placeholder = placeholders[type];
    byId('piece-panel').setAttribute('aria-labelledby', `${type}-tab`);
    tabs.forEach((tab) => {
      const active = tab.dataset.type === type;
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    renderContributors();
    renderReceipt();
    status(savedText ? 'All changes saved' : 'Not yet received');
  } catch (error) {
    status(error.message, true);
  } finally {
    busy = false;
    updateControls();
  }
}

tabs.forEach((tab, index) => {
  tab.addEventListener('click', () => {
    if (!busy && selected && tab.dataset.type !== pieceType && allowDiscard()) {
      loadPiece(selected, tab.dataset.type);
    }
  });
  tab.addEventListener('keydown', (event) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const shown = visibleTabs();
    const position = shown.indexOf(tab);
    const target = event.key === 'Home' ? shown[0] :
      event.key === 'End' ? shown.at(-1) :
      shown[(position + (event.key === 'ArrowRight' ? 1 : -1) + shown.length) % shown.length];
    target.focus();
    target.click();
  });
});

text.addEventListener('input', () => {
  status(pieceDirty() ? 'Unsaved changes' : 'All changes saved');
  updateControls();
});
byId('search').addEventListener('input', renderContributors);
byId('save').addEventListener('click', async () => {
  if (busy || !selected || !pieceDirty() || !text.value.trim()) return;
  busy = true;
  updateControls();
  status('Saving...');
  try {
    const record = await api(`/api/contributors/${selected.id}/pieces/${pieceType}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text.value }),
    });
    savedText = text.value;
    selected = record;
    contributors = contributors.map((entry) => entry.id === record.id ? record : entry);
    renderContributors();
    renderReceipt();
    status(`${labels[pieceType]} saved`);
  } catch (error) {
    status(error.message, true);
  } finally {
    busy = false;
    updateControls();
  }
});

byId('has-referee').addEventListener('change', () => {
  byId('referee-status').textContent = refereeDirty() ?
    'Unsaved answer' : 'Answer saved';
  updateControls();
});
byId('referee-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (busy || !selected || !refereeDirty()) return;
  busy = true;
  updateControls();
  byId('referee-status').textContent = 'Saving answer...';
  try {
    const record = await api(`/api/contributors/${selected.id}/referee`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ has_referee: refereeAnswer() }),
    });
    selected = record;
    contributors = contributors.map((entry) => entry.id === record.id ? record : entry);
    byId('referee-status').textContent = 'Answer saved';
  } catch (error) {
    byId('referee-status').textContent = error.message;
  } finally {
    busy = false;
    updateControls();
  }
});

byId('document-file').addEventListener('change', () => {
  const file = byId('document-file').files[0];
  byId('file-name').textContent = file?.name || 'Choose Word or PDF';
  updateControls();
});
byId('upload-document').addEventListener('click', async () => {
  const file = byId('document-file').files[0];
  if (busy || !selected || !file) return;
  busy = true;
  updateControls();
  status('Uploading document...');
  try {
    const form = new FormData();
    form.append('file', file);
    const record = await api(`/api/contributors/${selected.id}/pieces/${pieceType}/document`, {
      method: 'POST', body: form,
    });
    selected = record;
    contributors = contributors.map((entry) => entry.id === record.id ? record : entry);
    byId('document-file').value = '';
    byId('file-name').textContent = 'Choose Word or PDF';
    renderContributors();
    renderReceipt();
    status(`${labels[pieceType]} document uploaded`);
  } catch (error) {
    status(error.message, true);
  } finally {
    busy = false;
    updateControls();
  }
});

byId('add').addEventListener('click', () => {
  if (!allowDiscard()) return;
  byId('add-form').reset();
  byId('add-error').textContent = '';
  byId('add-dialog').showModal();
});
byId('cancel-add').addEventListener('click', () => byId('add-dialog').close());
byId('add-dialog').addEventListener('cancel', (event) => {
  if (creating) event.preventDefault();
});
byId('add-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (creating) return;
  creating = true;
  byId('create').disabled = true;
  byId('cancel-add').disabled = true;
  byId('add-error').textContent = '';
  try {
    const record = await api('/api/contributors', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: byId('new-name').value }),
    });
    contributors.push(record);
    contributors.sort((first, second) => first.name.localeCompare(second.name));
    byId('search').value = '';
    byId('add-dialog').close();
    renderContributors();
    await loadPiece(record, 'bio');
  } catch (error) {
    byId('add-error').textContent = error.message;
  } finally {
    creating = false;
    byId('create').disabled = false;
    byId('cancel-add').disabled = false;
  }
});

window.addEventListener('beforeunload', (event) => {
  if (dirty()) {
    event.preventDefault();
    event.returnValue = '';
  }
});

async function loadContributors() {
  const data = await api('/api/contributors');
  contributors = data.contributors;
  renderContributors();
  if (contributors.length) await loadPiece(contributors[0], 'bio');
}

byId('project-select').addEventListener('change', async () => {
  const selector = byId('project-select');
  if (!allowDiscard(true)) {
    selector.value = projectCode;
    return;
  }
  projectCode = selector.value;
  clearDocumentUpload();
  savedRequirements = null;
  selected = null;
  contributors = [];
  savedText = '';
  text.value = '';
  byId('contributor-name').textContent = 'No contributor selected';
  renderContributors();
  renderReceipt();
  busy = true;
  updateControls();
  status('Loading contributors...');
  try {
    await loadRequirements();
    await loadContributors();
    if (!contributors.length) status('Add a contributor to this project.');
  } catch (error) {
    status(error.message, true);
  } finally {
    busy = false;
    updateControls();
  }
});

requirementFields.forEach((field) => {
  byId(field).addEventListener('change', () => {
    requirementsStatus(requirementsDirty() ? 'Unsaved requirements' : 'Requirements unchanged');
    updateControls();
  });
});

byId('requirements-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (busy || creating || !projectCode || !requirementsDirty()) return;
  busy = true;
  updateControls();
  requirementsStatus('Saving requirements...');
  try {
    const data = await api(`/api/editor/projects/${encodeURIComponent(projectCode)}/requirements`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requirementValues()),
    });
    savedRequirements = data.requirements;
    requirementsStatus('Requirements saved.');
  } catch (error) {
    requirementsStatus(error.message, true);
  } finally {
    busy = false;
    updateControls();
  }
});

async function initialize() {
  if (window.lucide) window.lucide.createIcons();
  busy = true;
  updateControls();
  try {
    try {
      const data = await api('/api/editor/projects');
      const selector = byId('project-select');
      data.projects.forEach((project) => {
        const option = document.createElement('option');
        option.value = project.code;
        option.textContent = `${project.name} (${project.code.slice(0, 8)})`;
        selector.append(option);
      });
      projectsAvailable = true;
      byId('project-status').textContent = data.projects.length ?
        'Select a book to manage its contributors.' :
        'No edited volumes yet. Create one through the Projects API.';
    } catch (error) {
      byId('project-status').textContent = `Could not load projects: ${error.message}`;
    }
    await loadContributors();
  } catch (error) {
    byId('list-status').textContent = error.message;
    status(error.message, true);
  } finally {
    busy = false;
    updateControls();
  }
}
initialize();