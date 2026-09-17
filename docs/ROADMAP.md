# Roadmap

The original `unocrprompt.md` is the scope baseline. No pre-existing roadmap was
present; these milestones translate its requirements into reviewable work.
Scope update (2026-09-17): user requested PDF testing and flexible file sizes.
PDFs and configurable upload limits are now included; the original brief is retained.

| Milestone | Deliverables and acceptance | Current state |
| --- | --- | --- |
| 1. Foundation | FastAPI/vanilla layout, AGENTS.md, documentation, ignored caches/weights | Implemented |
| 2. Setup | Vendor clone; separate CPU/CUDA requirements; cross-platform launcher; exact setup instructions | Implemented; full dependency installs unverified |
| 3. Backend | Device endpoint; lazy singleton; serialized infer; text/timing; readable failures; upload validation and cleanup | Implemented; six mocked API tests passed; real model validation pending |
| 4. Frontend | Browse/drop, preview, disabled busy button/spinner, device badge, text/timing/errors | Implemented; four PDF-selection DOM tests passed; cache fix tested; interactive browser validation pending |
| 5. CPU acceptance | Install on non-CUDA host; boot; upload/error checks; attempt first model load and record result | Python 3.12.10 installed locally in `env`; application dependency install and model run pending |
| 6. CUDA acceptance | Install on 16 GB GPU; verify bfloat16; first and cached inference; output accuracy/time/peak VRAM | Pending suitable hardware |
| 7. PDF and flexible uploads | Sequential PDF OCR, ordered page results, no default byte cap, optional configured cap, malformed/encrypted PDF errors, cleanup | Implemented; 12 API tests and JS syntax check passed; real PDF OCR pending |

## Required completion evidence

Record commands, versions, hardware, observed outcomes, and failures in
`VALIDATION.md`. Mocked tests validate HTTP behavior, not model compatibility.
Do not mark milestones 5 or 6 complete based on static checks or stubbed outputs.

## Deferred work

CPU attention/device porting, multiple-file batch jobs, streaming tokens, authentication,
deployment, and alternative OCR models are beyond this local document UI.
A CPU port requires work in upstream custom code; an eager-attention flag alone
cannot fix explicit CUDA calls. Any scope extension needs roadmap documentation.
