End-to-end music deconstruction tool: separates a song into stems (Demucs), transcribes each to MIDI, analyzes tempo/key/chords/harmony, engraves a score, and exports Reaper/.dawproject/FL Studio projects — all packed into a single `.demixer` archive. Python 3.11 CLI with an optional PySide6 desktop shell.

## Current phase

### 2026-11-09 — installation and CI hardening

- Declared the supported runtime imports and added optional `worker`, `gui`, and
  `roformer` dependency groups. CLI help and test collection no longer import
  PyTorch; the model dependency is loaded only when separation is requested.
- Fixed loop detection choosing a later harmonic when floating-point noise gave
  it a marginally higher correlation score; the detector now selects its earliest
  qualifying candidate. Added focused loop tests and touched-module lint to CI.
- Added a clean Python 3.11 CI job for CLI smoke checks and focused functional
  tests. It does not install model workers or fetch model checkpoints.
- Aligned the package and bundle version at 0.2.0. Clean-environment validation
  passed CLI help, lock consistency, focused Ruff, and the focused writer/loop
  tests (32 in the first run; the loop regression then passed as 7 tests and the
  DAWproject version check as 5 tests). Full repository Ruff still has
  pre-existing findings; no hosted CI run is claimed.
- Integration preserved the remote CLI lazy-import fix and attribution workflow.
  The combined CLI/writer/loop selection passed 37 tests in 1.02 seconds; no
  broad suite, model inference or workflow dispatch ran during integration.
- DAWproject application metadata now reads the package version instead of a
  stale hard-coded 0.0.1; the focused writer test checks the version field.

Earlier pipeline validation (2026-05-24) covered 20+ genres and reported 129
passing tests; Isophonics results were key 0.763, tempo 0.916, and chord majmin
0.752 with BTC. That historical result does not replace the clean-install CI
baseline added above.

Outstanding work:
- **ADTOF drums**: shipped opt-in (`--drums adtof`, onset-F1 0.975 vs 0.825 spectral); not promoted to default pending an ear-check on real-stem class accuracy.
- **YourMT3+ polyphony**: upgrade path researched and attempted; blocked by upstream breakage (inference adapter broken, pytorch-port LFS smudge broken as of 2026-05-24).
- **Score engraving quality**: current fixed 16th-grid quantization is robust but naive; learned rhythm quantization (arXiv:2508.19262) identified as the highest perceived-quality gain — medium-high effort, deferred.

## revoy ledger block

<!-- revoy:begin -->
```toml
phase = "post-audit hardening"

[[todo]]
line = "Promote ADTOF drums to default after an ear-check on real-stem class accuracy vs the spectral classifier"
difficulty = 15
priority = "MED"

[[todo]]
line = "Unblock YourMT3+ worker once upstream inference adapter or pytorch-port LFS is fixed; add --transcriber yourmt3 option and A/B vs basic-pitch on polyphonic stems"
difficulty = 40
priority = "LOW"

[[todo]]
line = "Replace fixed-16th-grid quantize.py with a learned rhythm-quantization stage (2508.19262 approach) for human-readable scores; keep grid-snap as fallback"
difficulty = 65
priority = "LOW"

[[todo]]
line = "CLAP/VST3 companion plugin for one-click .demixer load in any DAW (nih-plug; design documented in docs/DAW_INTEGRATION_PLAN.md)"
difficulty = 80
priority = "VLOW"
```
<!-- revoy:end -->
