const $ = (id) => document.getElementById(id);
let selectedFile = null;
let previewUrl = null;
let running = false;
let maxUploadBytes = 0;

function showError(message) {
  $('error').textContent = message;
  $('error').hidden = !message;
}

function selectFile(file) {
  if (running) return;
  selectedFile = null;
  $('run').disabled = true;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = null;
  $('preview').hidden = true;
  $('preview').removeAttribute('src');
  $('pdf-note').hidden = true;
  $('filename').textContent = 'No file selected';
  showError('');
  if (!file) return;
  const isPdf = file.type === 'application/pdf' || /\.pdf$/i.test(file.name);
  if (!isPdf && !['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
    showError('Choose a PDF, PNG, JPEG, or WebP file.');
    return;
  }
  if (!file.size || (maxUploadBytes && file.size > maxUploadBytes)) {
    showError(file.size ? `File exceeds the configured ${maxUploadBytes} byte limit.` : 'Choose a non-empty file.');
    return;
  }
  selectedFile = file;
  if (isPdf) {
    $('pdf-note').hidden = false;
  } else {
    previewUrl = URL.createObjectURL(file);
    $('preview').src = previewUrl;
    $('preview').hidden = false;
  }
  $('filename').textContent = `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MiB)`;
  $('run').disabled = false;
  $('result').textContent = 'Your extracted text will appear here.';
  $('timing').textContent = 'Awaiting run';
  $('status').textContent = isPdf ? 'PDF ready. All pages will be processed in order.' : 'Image ready.';
}

$('file').addEventListener('change', (event) => selectFile(event.target.files[0]));
for (const eventName of ['dragenter', 'dragover', 'dragleave', 'drop']) {
  $('dropzone').addEventListener(eventName, (event) => {
    event.preventDefault();
    $('dropzone').classList.toggle('dragging', !running && ['dragenter', 'dragover'].includes(eventName));
    if (eventName === 'drop') selectFile(event.dataTransfer.files[0]);
  });
}

$('run').addEventListener('click', async () => {
  if (!selectedFile || running) return;
  running = true;
  $('run').disabled = true;
  $('file').disabled = true;
  $('spinner').hidden = false;
  $('run-label').textContent = 'Processing…';
  $('status').textContent = 'Loading model and extracting text. First use may download weights; see the server log for progress.';
  $('result').textContent = '';
  $('timing').textContent = 'Processing';
  showError('');
  try {
    const body = new FormData();
    body.append('file', selectedFile);
    const response = await fetch('/api/ocr', { method: 'POST', body });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'The request could not be processed.');
    $('result').textContent = data.text || 'No text detected.';
    $('timing').textContent = `${data.inference_seconds.toFixed(2)} s inference`;
    $('status').textContent = `Extraction complete${data.page_count ? `: ${data.page_count} pages` : ''}. Timing excludes model loading and PDF rendering.`;
  } catch (error) {
    showError(error.message);
    $('timing').textContent = 'Unsuccessful';
    $('status').textContent = 'OCR could not complete. See the error below.';
  } finally {
    running = false;
    $('run').disabled = !selectedFile;
    $('file').disabled = false;
    $('spinner').hidden = true;
    $('run-label').textContent = 'Run OCR';
  }
});

async function loadDevice() {
  try {
    const response = await fetch('/api/system-info');
    if (!response.ok) throw new Error('Device detection failed');
    const data = await response.json();
    $('device').textContent = data.device === 'cuda' ? `${data.device_name} · ${data.vram_gb} GB VRAM` : 'CPU · Experimental inference';
  } catch {
    $('device').textContent = 'Device unavailable';
  }
}
loadDevice();

async function loadUploadConfig() {
  try {
    const response = await fetch('/api/upload-config');
    if (!response.ok) throw new Error('Configuration unavailable');
    const data = await response.json();
    maxUploadBytes = data.max_upload_bytes;
    $('upload-hint').textContent = maxUploadBytes
      ? `or click to browse · limit ${(maxUploadBytes / 1024 / 1024).toFixed(1)} MiB`
      : 'or click to browse · no fixed file-size limit';
  } catch {
    $('upload-hint').textContent = 'or click to browse · server validates file size';
  }
}
loadUploadConfig();
