'use strict';

const byId = (id) => document.getElementById(id);

// The piece box. When Toast UI loaded from its CDN, this is a Word-like
// editor that saves markdown, so contributors can format text without
// knowing markdown (issue #20). If the CDN could not be reached, it is the
// plain textarea. The rest of this file only uses these five functions,
// so it works the same either way.
const piece = (() => {
  const box = byId('piece-text');
  const plain = {
    value: () => box.value,
    setValue: (value) => { box.value = value; },
    setDisabled: (disabled) => { box.disabled = disabled; },
    setPlaceholder: (value) => { box.placeholder = value; },
    onChange: (handler) => box.addEventListener('input', handler),
  };
  if (!window.toastui?.Editor) return plain;
  const holder = byId('piece-editor');
  holder.hidden = false;
  let editor;
  try {
    editor = new window.toastui.Editor({
      el: holder,
      height: '440px',
      initialEditType: 'wysiwyg',
      hideModeSwitch: true,
      // Don't send usage data to Toast UI's servers.
      usageStatistics: false,
      toolbarItems: [['heading', 'bold', 'italic', 'strike'], ['ul', 'ol', 'quote'], ['link']],
      // Pasted or dropped images would be saved inside the text; ignore them.
      hooks: { addImageBlobHook: () => false },
    });
  } catch (error) {
    holder.hidden = true;
    return plain;
  }
  box.hidden = true;
  // The page's "Biography" label points at the hidden textarea, so name the
  // editor's typing area for screen readers too...
  holder.querySelectorAll('[contenteditable]').forEach((area) => {
    area.setAttribute('aria-labelledby', 'piece-label');
  });
  // ...and make clicking the label put the cursor in the editor.
  byId('piece-label').addEventListener('click', (event) => {
    event.preventDefault();
    if (!holder.inert) editor.focus();
  });

  // Forget the undo history, so Undo can't bring back text from before the
  // last load (for example the previous contributor's bio, which Save would
  // then store on this contributor). Toast UI 3.2.2 has no public way to do
  // this, so reset its ProseMirror state directly; the version is pinned in
  // editor.html.
  function clearUndoHistory() {
    const view = editor.wwEditor?.view;
    if (!view) return;
    const { state } = view;
    view.updateState(state.constructor.create({
      doc: state.doc, selection: state.selection, plugins: state.plugins,
    }));
  }

  // True while the code (not the person) is filling the editor, so that
  // doesn't count as typing.
  let filling = false;
  // Whether the typing area had focus when the editor was locked.
  let hadFocus = false;
  return {
    value: () => editor.getMarkdown(),
    setValue: (value) => {
      filling = true;
      try {
        editor.setMarkdown(value, false);
        clearUndoHistory();
      } finally {
        filling = false;
      }
    },
    setDisabled: (disabled) => {
      if (disabled === holder.inert) return;
      if (disabled) hadFocus = holder.contains(document.activeElement);
      // inert blocks clicks, typing and focus inside the editor.
      holder.inert = disabled;
      holder.classList.toggle('is-disabled', disabled);
      if (!disabled && hadFocus) {
        hadFocus = false;
        editor.focus();
      }
    },
    setPlaceholder: (value) => editor.setPlaceholder?.(value),
    onChange: (handler) => editor.on('change', () => { if (!filling) handler(); }),
  };
})();
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
// What the box held right after loading or saving. Toast UI may tidy the
// markdown when it loads (for example * bullets become -), so unsaved
// changes are measured against this, not against the server's text.
let baseline = '';
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
    const data = await api(`/Projects/requirements/${encodeURIComponent(projectCode)}`);
    savedRequirements = data.requirements;
    requirementFields.forEach((field) => { byId(field).checked = savedRequirements[field]; });
    requirementsStatus('Requirements loaded.');
  } catch (error) {
    requirementsStatus(`Could not load requirements: ${error.message} Refresh the page to retry.`, true);
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

const MAX_LENGTH = 100000;

// The textarea's maxlength doesn't apply to Toast UI, so check it here.
// (The saved markdown counts, including formatting marks.)
function tooLong() {
  return piece.value().length > MAX_LENGTH;
}

function pieceDirty() {
  return selected !== null && piece.value() !== baseline;
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
  piece.setDisabled(busy || selected === null);
  byId('save').disabled = busy || !pieceDirty() || !piece.value().trim() || tooLong();
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
  byId('character-count').textContent = `${piece.value().length.toLocaleString()} / 100,000`;
  byId('character-count').classList.toggle('error', tooLong());
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
    piece.setValue(savedText);
    baseline = piece.value();
    byId('has-referee').value = record.HasReferee === true ? 'yes' :
      record.HasReferee === false ? 'no' : '';
    byId('referee-status').textContent = record.HasReferee === null ||
      record.HasReferee === undefined ? 'No answer saved' : 'Answer saved';
    byId('contributor-name').textContent = record.name;
    byId('piece-label').textContent = labels[type];
    piece.setPlaceholder(placeholders[type]);
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

piece.onChange(() => {
  if (tooLong()) status('Pieces must be at most 100,000 characters. Shorten the text to save.', true);
  else status(pieceDirty() ? 'Unsaved changes' : 'All changes saved');
  updateControls();
});
byId('search').addEventListener('input', renderContributors);
byId('save').addEventListener('click', async () => {
  if (busy || !selected || !pieceDirty() || !piece.value().trim() || tooLong()) return;
  busy = true;
  updateControls();
  status('Saving...');
  try {
    const sent = piece.value();
    const record = await api(`/api/contributors/${selected.id}/pieces/${pieceType}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: sent }),
    });
    savedText = sent;
    baseline = sent;
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
  piece.setValue('');
  baseline = '';
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
    const data = await api(`/Projects/requirements/${encodeURIComponent(projectCode)}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
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
    // On a project's Contributors page the project is already chosen,
    // so load its requirements and contributors right away.
    const pageProject = document.body.dataset.project;
    if (pageProject) {
      projectCode = pageProject;
      byId('project-select').value = pageProject;
      await loadRequirements();
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