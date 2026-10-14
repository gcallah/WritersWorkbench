'use strict';

const byId = (id) => document.getElementById(id);
const text = byId('piece-text');
const tabs = [...document.querySelectorAll('[data-type]')];
const labels = { bio: 'Biography', submission: 'Submission' };
const flags = { bio: 'Bio', submission: 'Submission' };
let contributors = [];
let selected = null;
let pieceType = 'bio';
let savedText = '';
let busy = false;
let creating = false;

async function api(path, options = {}) {
  const url = new URL(path, location.origin);
  const response = await fetch(url, { credentials: 'same-origin', ...options });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'The request failed.');
  return data;
}

function status(message, error = false) {
  byId('save-status').textContent = message;
  byId('save-status').classList.toggle('error', error);
}

function dirty() {
  return selected !== null && text.value !== savedText;
}

function allowDiscard() {
  return !dirty() || confirm('Discard unsaved changes?');
}

function updateControls() {
  text.disabled = busy || selected === null;
  byId('save').disabled = busy || !dirty() || !text.value.trim();
  byId('add').disabled = busy;
  tabs.forEach((tab) => { tab.disabled = busy || selected === null; });
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
  updateControls();
  status('Loading...');
  try {
    const data = await api(`/api/contributors/${record.id}/pieces/${type}`);
    selected = record;
    pieceType = type;
    savedText = data.text;
    text.value = savedText;
    byId('contributor-name').textContent = record.name;
    byId('piece-label').textContent = labels[type];
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
    const target = event.key === 'Home' ? tabs[0] : event.key === 'End' ? tabs.at(-1) : tabs[1 - index];
    target.focus();
    target.click();
  });
});

text.addEventListener('input', () => {
  status(dirty() ? 'Unsaved changes' : 'All changes saved');
  updateControls();
});
byId('search').addEventListener('input', renderContributors);
byId('save').addEventListener('click', async () => {
  if (busy || !selected || !dirty() || !text.value.trim()) return;
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

async function initialize() {
  if (window.lucide) window.lucide.createIcons();
  busy = true;
  updateControls();
  try {
    const data = await api('/api/contributors');
    contributors = data.contributors;
    renderContributors();
    if (contributors.length) await loadPiece(contributors[0], 'bio');
  } catch (error) {
    byId('list-status').textContent = error.message;
    status(error.message, true);
  } finally {
    busy = false;
    updateControls();
  }
}
initialize();