const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function loadUI() {
  const root = path.join(__dirname, '..');
  const html = fs.readFileSync(path.join(root, 'frontend/index.html'), 'utf8');
  const elements = new Map([...html.matchAll(/id="([^"]+)"/g)].map((match) => [match[1], {
    hidden: true, disabled: true, textContent: '', events: {},
    removeAttribute(name) { delete this[name]; },
    addEventListener(name, callback) { this.events[name] = callback; },
    classList: { toggle() {} },
  }]));
  const context = vm.createContext({
    document: { getElementById: (id) => elements.get(id) },
    URL: { createObjectURL: () => 'blob:test', revokeObjectURL() {} },
    fetch: async () => ({ ok: true, json: async () => ({ device: 'cpu', max_upload_bytes: 0 }) }),
  });
  vm.runInContext(fs.readFileSync(path.join(root, 'frontend/app.js'), 'utf8'), context);
  return elements;
}

for (const type of ['application/pdf', '', 'application/octet-stream']) {
  test(`PDF selection enables OCR and shows filename with MIME ${type || '(empty)'}`, () => {
    const ui = loadUI();
    ui.get('file').events.change({ target: { files: [{ name: 'Report.PDF', type, size: 20 * 1024 * 1024 }] } });
    assert.equal(ui.get('run').disabled, false);
    assert.equal(ui.get('pdf-note').hidden, false);
    assert.match(ui.get('filename').textContent, /Report.PDF/);
    assert.equal(ui.get('error').hidden, true);
  });
}

test('dropping a PDF recovers after unsupported-file validation', () => {
  const ui = loadUI();
  ui.get('file').events.change({ target: { files: [{ name: 'file.txt', type: 'text/plain', size: 10 }] } });
  assert.equal(ui.get('run').disabled, true);
  ui.get('dropzone').events.drop({ preventDefault() {}, dataTransfer: { files: [{ name: 'file.pdf', type: 'application/pdf', size: 10 }] } });
  assert.equal(ui.get('run').disabled, false);
  assert.equal(ui.get('pdf-note').hidden, false);
  assert.equal(ui.get('error').hidden, true);
});
