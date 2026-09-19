<!-- Track reliability changes requested in fixes.md separately from hardware acceptance. -->
# Roadmap

The original `unocrprompt.md` is the scope baseline. No pre-existing roadmap was
present; these milestones translate its requirements into reviewable work.
Scope update (2026-09-17): user requested PDF testing and flexible file sizes.
PDFs and configurable upload limits are now included; the original brief is retained.

| Milestone | Deliverables and acceptance | Current state |
| --- | --- | --- |
| 1. Foundation | FastAPI/vanilla layout, AGENTS.md, documentation, ignored caches/weights | Implemented |
| 2. Setup | Vendor clone; separate CPU/CUDA requirements; cross-platform launcher; exact setup instructions | Implemented; full dependency installs unverified |
| 3. Backend | Device endpoint; startup singleton; serialized infer; text/timing; readable failures; upload validation and cleanup | Implemented; six mocked API tests passed; real model validation pending |
| 4. Frontend | Browse/drop, preview, disabled busy button/spinner, device badge, text/timing/errors | Implemented; four PDF-selection DOM tests passed; cache fix tested; interactive browser validation pending |
| 5. Non-CUDA acceptance | Boot UI without loading the model; disable OCR with readable 503 | Implemented; live CPU smoke test and validation recorded below |
| 6. CUDA acceptance | Install on 16 GB GPU; verify bfloat16; first and cached inference; output accuracy/time/peak VRAM | Pending suitable hardware |
| 7. PDF and flexible uploads | Sequential PDF OCR, ordered page results, no default byte cap, optional configured cap, malformed/encrypted PDF errors, cleanup | Implemented; 12 API tests and JS syntax check passed; real PDF OCR pending |

## Reliability update from fixes.md

- Setup now caches the model before serving; startup loads from cache with readiness.
- PDFs use an in-process background worker with partial page output and polling.
- Results grow up to 70vh, then scroll. One document at a time and 20 retained jobs.
- 17 backend tests, eight frontend tests, and syntax checks passed. Setup caching
  and real CPU startup loading passed; long CUDA runs remain pending. See VALIDATION.md.
- CUDA success described in fixes.md is user-provided context, not a new local measurement.

## Required completion evidence

Record commands, versions, hardware, observed outcomes, and failures in
`VALIDATION.md`. Mocked tests validate HTTP behavior, not model compatibility.
Do not mark milestones 5 or 6 complete based on static checks or stubbed outputs.

## Deferred work

CPU attention/device porting, multiple-file batch jobs, streaming tokens, authentication,
deployment, and alternative OCR models are beyond this local document UI.
A CPU port requires work in upstream custom code; an eager-attention flag alone
cannot fix explicit CUDA calls. Any scope extension needs roadmap documentation.

## Automatic setup and CUDA status update (2026-09-19)

Approved scope now prohibits CPU model loading and skips non-CUDA weight downloads
unless explicitly requested. Earlier CPU loading evidence above is historical,
not the current acceptance criterion. Added automatic Windows Python 3.12 setup,
requirements hash stamps, download retries/free-space checks, file-only caching,
readiness banner, and OCR_MAX_LENGTH (16384 default).

Implementation and automated validation are recorded in VALIDATION.md. Remaining
hardware acceptance: real CUDA setup/inference, 16 GB VRAM behavior, Windows Python
installation on a clean machine, and interactive browser auto-opening. No mocked
CUDA test is evidence of GPU compatibility. The original brief remains unchanged.

Validation for this update: 33 Python tests (unittest and pytest), 13 frontend
tests, JS syntax, repeat CPU setup, and the live 30.19-second CPU smoke passed.
