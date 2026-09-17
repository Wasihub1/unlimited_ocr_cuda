// Exercise readiness gating alongside PDF selection with the actual frontend script.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

async function loadUI(status = "ready", jobStatus = "done") {
  let polls = 0;
  const progressSnapshots = [];
  const root = path.join(__dirname, '..');
  const html = fs.readFileSync(path.join(root, 'frontend/index.html'), 'utf8');
  const elements = new Map([...html.matchAll(/id="([^"]+)"/g)].map((match) => [match[1], {
    hidden: true, disabled: true, textContent: '', events: {},
    removeAttribute(name) { delete this[name]; },
    addEventListener(name, callback) { this.events[name] = callback; },
    classList: { toggle() {} },
  }]));
  const context = vm.createContext({
    setTimeout(callback, delay) {
      if (delay === 2000) {
        progressSnapshots.push(elements.get('result').textContent);
        callback();
      }
    },
    FormData: class { append() {} },
    sessionStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
    document: { getElementById: (id) => elements.get(id) },
    URL: { createObjectURL: () => 'blob:test', revokeObjectURL() {} },
    fetch: async (url) => ({ ok: true, json: async () => {
      if (url === '/api/ocr') return { job_id: 'job-test' };
      if (url.startsWith('/api/ocr/status/')) {
        polls++;
        return { status: polls === 1 ? 'processing' : jobStatus, pages_done: 1,
          total_pages: 2, results: [{ page: 1, text: 'Partial page' }],
          text: 'Complete text', inference_seconds: 0.5, page_count: 2, error: 'Page 2 failed' };
      }
      return { device: 'cpu', max_upload_bytes: 0, model_status: status };
    } }),
  });
  vm.runInContext(fs.readFileSync(path.join(root, 'frontend/app.js'), 'utf8'), context);
  await new Promise(resolve => setImmediate(resolve));
  elements.progressSnapshots = progressSnapshots;
  return elements;
}

for (const type of ['application/pdf', '', 'application/octet-stream']) {
  test(`PDF selection enables OCR and shows filename with MIME ${type || '(empty)'}`, async () => {
    const ui = await loadUI();
    ui.get('file').events.change({ target: { files: [{ name: 'Report.PDF', type, size: 20 * 1024 * 1024 }] } });
    assert.equal(ui.get('run').disabled, false);
    assert.equal(ui.get('pdf-note').hidden, false);
    assert.match(ui.get('filename').textContent, /Report.PDF/);
    assert.equal(ui.get('error').hidden, true);
  });
}

test('dropping a PDF recovers after unsupported-file validation', async () => {
  const ui = await loadUI();
  ui.get('file').events.change({ target: { files: [{ name: 'file.txt', type: 'text/plain', size: 10 }] } });
  assert.equal(ui.get('run').disabled, true);
  ui.get('dropzone').events.drop({ preventDefault() {}, dataTransfer: { files: [{ name: 'file.pdf', type: 'application/pdf', size: 10 }] } });
  assert.equal(ui.get('run').disabled, false);
  assert.equal(ui.get('pdf-note').hidden, false);
  assert.equal(ui.get('error').hidden, true);
});

for (const status of ['loading', 'error']) {
  test(`OCR remains disabled while model status is ${status}`, async () => {
    const ui = await loadUI(status);
    ui.get('file').events.change({ target: { files: [{ name: 'test.pdf', type: 'application/pdf', size: 10 }] } });
    assert.equal(ui.get('run').disabled, true);
    assert.match(ui.get('model-status').textContent, /Model/);
  });
}

for (const terminal of ['done', 'error']) {
  test(`PDF polling renders partial output before ${terminal}`, async () => {
    const ui = await loadUI('ready', terminal);
    ui.get('file').events.change({ target: { files: [{ name: 'test.pdf', type: 'application/pdf', size: 10 }] } });
    await ui.get('run').events.click();
    assert.match(ui.progressSnapshots[0], /Page 1.*\nPartial page/);
    assert.equal(ui.get('progress').value, 1);
    assert.equal(ui.get('run').disabled, false);
    if (terminal === 'error') {
      assert.match(ui.get('result').textContent, /Partial page/);
      assert.match(ui.get('error').textContent, /Page 2 failed/);
    } else {
      assert.equal(ui.get('result').textContent, 'Complete text');
    }
  });
}
