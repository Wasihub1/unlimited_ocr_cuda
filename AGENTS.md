<!-- Updated lifecycle requirements from fixes.md supersede original lazy loading. -->
# Project instructions

Build the local Unlimited-OCR test application described in `unocrprompt.md`.
Read `docs/ROADMAP.md` before changing scope; update its evidence and remaining
work when completing a milestone. Keep the original prompt as the source brief.
The approved scope also includes PDFs and flexible upload sizes: process PDF
pages sequentially, preserve page order, and default to no upload byte cap.

- Use Python/FastAPI and vanilla HTML/CSS/JavaScript. No React, Vue, Streamlit,
  Gradio, database, authentication, or hosted service is needed for this scope.
- Keep hardware detection in `app/device.py`, configuration in `app/config.py`,
  model lifecycle in `app/model_loader.py`, and HTTP handling in `app/routes/`.
- Cache weights during setup on CUDA hosts (or explicit force-download); load once
  at startup in a background thread only when CUDA is available. Never construct
  the model on CPU. Expose loading/ready/error/unavailable_no_cuda and reject OCR until ready. Serialize inference. Keep the UI and
  system-info route usable before a model is loaded and after a model error.
- Use AutoModel/AutoTokenizer and the actual upstream infer API. Verify upstream
  interfaces before changing integration. Never invent OCR results or claim CPU
  inference or 16 GB CUDA support without a real hardware run.
- CPU resolves to float32; CUDA resolves to bfloat16. Surface CUDA-only failures
  clearly; do not silently monkeypatch tensor device operations.
- Keep CPU/CUDA requirements separate. Never commit weights, environments,
  downloaded vendor contents, uploads, or model caches.
- Serve only frontend assets. Validate documents, support configurable upload limits, clean temporary
  files, and render model output as text, not HTML.
- Keep `README.md` as the setup entry point. Save API/architecture decisions in
  `docs/ARCHITECTURE.md`, milestone tracking in `docs/ROADMAP.md`, and actual
  validation evidence in `docs/VALIDATION.md`. Distinguish implemented from tested.
- Run `python -m unittest discover -s tests -v` for backend changes and
  `node --check frontend/app.js` for JavaScript changes. Record unavailable checks.
- Use one uvicorn worker to avoid multiple model copies. Default to localhost.

- PDFs return job IDs and publish per-page progress/results; preserve partial output
  on failure. Use one in-process worker, clean temporary files, and document that
  jobs are not durable across restarts. Follow `fixes.md` for these scope changes.
