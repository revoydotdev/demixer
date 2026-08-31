<div align="center">

# demixer

### Audio analysis and production handoff, from one track

Separate a recording into stems, derive MIDI and musical analysis, engrave a score,
and assemble DAW-oriented project files in one inspectable bundle.

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Desktop GUI](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt-41CD52)](https://pypi.org/project/PySide6/)
[![License: AGPL-3.0-or-later](https://img.shields.io/badge/License-AGPL--3.0--or--later-3DA639)](https://www.gnu.org/licenses/agpl-3.0.html)
[![Status: experimental](https://img.shields.io/badge/Status-experimental-8B5CF6)](https://github.com/revoydotdev/demixer)

</div>

demixer is an experimental, desktop-oriented Python pipeline for turning an audio
file into production material: separated stems, per-stem MIDI where transcription
succeeds, tempo/key/chord analysis, a MusicXML score, and project files for several
DAW workflows. It is designed for exploration and handoff, not as a substitute for
critical listening or editorial review. Source separation, transcription, beat
tracking, and chord recognition are estimates and should be checked before release
or performance use.

## At a glance

```text
audio file
    |
    +-- ingest             ffmpeg decode -> 44.1 kHz stereo normalization
    +-- separation         Demucs stems (four or six sources)
    +-- musical analysis   beats, downbeats, tempo, key, chords
    +-- transcription      pitched parts and drums -> MIDI
    +-- score              quantized MIDI -> MusicXML -> SVG / optional MuseScore renders
    +-- DAW handoff        Reaper, DAWproject, FL Studio, and drag-in material
    `-- archive            directory bundle + sibling .demixer ZIP
```

The command-line entry point is `demixer process`; an optional Qt desktop shell
launches the same pipeline in a child process and streams its log and progress.

## Capabilities

| Area | Current implementation |
| --- | --- |
| Separation | Demucs `htdemucs` (default), `htdemucs_ft`, or six-source `htdemucs_6s`; a BS-RoFormer vocals replacement is available only when its isolated worker is installed. |
| Timing and tonality | `beat_this` beat/downbeat tracking with a librosa fallback; key estimation uses Essentia, preferring a drums-excluded mix after separation. |
| Chords | BTC is the CLI default and runs in an isolated worker; `autochord` is the in-environment alternative. Both results are retained as time-stamped chord segments. |
| MIDI | Basic Pitch is the default for pitched stems. With `--transcriber mt3`, MT3 handles `other`, `piano`, and `guitar`; bass and vocals remain on Basic Pitch. Drums use the spectral classifier by default or the isolated ADTOF worker. |
| Notation | MIDI is quantized and written as MusicXML, then rendered to SVG with Verovio. PDF and MSCZ are requested by default but are emitted only when MuseScore is available; PNG and MP3 preview rendering are opt-in. |
| Project handoff | Reaper `.rpp`, `.dawproject`, FL Studio `.flp`, FL Studio piano-roll scripts, and a drag-in folder containing metadata and references to the top-level stems/MIDI. |
| Harmony | `--harmony` writes harmonic descriptors, transitions, and substitutions. `--reharmonize` additionally writes a block-chord MIDI progression. |

The pipeline continues past several optional-stage failures so that successful
artifacts can still be bundled. A completed command therefore means the requested
pipeline reached its end, not that every optional model or renderer produced an
artifact; review the log and bundle contents.

## Command line

After preparing a complete runtime environment, process one source file into a
specific bundle directory:

```bash
demixer process "song.flac" -o build/song
```

Useful variations:

```bash
# Use the six-source Demucs model and preserve floating-point stem samples.
demixer process song.flac -o build/song --model htdemucs_6s --stem-format float

# Choose isolated-worker alternatives when those workers have been set up.
demixer process song.flac -o build/song \
  --transcriber mt3 --chords btc --drums adtof --roformer-vocals

# Treat a supplied or sibling MIDI file as the authority for tempo and meter.
demixer process song.flac -o build/song --midi-hint auto

# Ask for harmonic analysis and a reharmonized MIDI sketch.
demixer process song.flac -o build/song --harmony --reharmonize tritone

# Iterate without the slowest stages.
demixer process song.flac -o build/song --skip separate --skip transcribe
```

Run `demixer process --help` in a prepared environment for the full option list.
Notable controls include repeat-aware separation (`--detect-loops`), compact
archives (`--compact-archive`), selectable stem formats, score-render formats, and
individual stage skips.

## Bundle contents

With the default PCM-24 stem format, a successful full run to `build/song` is
organized approximately as follows. Optional files appear only when their stages
succeed and have not been skipped.

```text
build/song/
├── manifest.json              bundle schema, version, model labels, file list
├── analysis.json              source hash, loudness, tempo, beats, key, chords
├── stems/                     separated audio stems
├── midi/                      transcribed stem MIDI
├── score.musicxml             engraved-score source
├── score/                     Verovio SVG pages
├── score.pdf / score.mscz     when MuseScore is available and requested
├── song.rpp                   Reaper project
├── song.dawproject            DAWproject archive
├── song.flp                   FL Studio project
├── flstudio_scripts/          FL Studio piano-roll scripts
├── dragin/                    DAW-agnostic metadata and import guidance
├── harmony.json               with --harmony or --reharmonize
└── reharmonization.mid        with --reharmonize

build/song.demixer             ZIP snapshot of the bundle directory
```

`--compact-archive` omits loose `stems/` from the ZIP only when a DAWproject file
is present, because that format embeds the audio. The unarchived bundle keeps its
stems. If analysis is skipped, the command instead writes a minimal partial
`manifest.json` and returns without the normal bundle artifacts.

## Desktop application

The PySide6 application provides drag-and-drop or file-picker input, engine
selection, a live subprocess log, cancellation, and a file tree for the resulting
output directory. It is exposed as the `demixer-gui` GUI script after installing
the package's `gui` extra.

```bash
uv run --extra gui demixer-gui
```

The GUI selects the same engines and invokes `python -m demixer.cli process`; it
does not provide a separate processing backend.

## Requirements and current installation status

The published package metadata targets **Python >=3.11,<3.12** and declares the
`demixer` CLI plus the optional `demixer-gui` script. [uv](https://docs.astral.sh/uv/)
is the repository's package manager. Audio ingest requires
[FFmpeg](https://ffmpeg.org/) on `PATH`; [MuseScore](https://github.com/musescore/MuseScore) is
needed only for PDF, MSCZ, PNG, and audio score renders.

The repository does **not yet declare its runtime pipeline dependencies** in
`pyproject.toml` (`project.dependencies` is empty). Consequently, a fresh
`uv sync`, including the declared `dev` and `gui` extras, does not currently make
the CLI runnable: imports such as NumPy and the audio/ML stack are absent. The
optional research engines also require their own repository-root virtual
environments (`.venv-btc`, `.venv-mt3`, `.venv-adtof`, and `.venv-roformer`) and,
for BTC, a local `third_party/BTC` checkout and checkpoint.

This is a known distribution gap, not a supported one-command installation path.
Until runtime dependencies and worker setup are published, use a pre-provisioned
development environment or treat the repository as source and test material.

Package metadata and generated bundle manifests currently report version `0.1.0`.

## Development and evaluation

The test suite exercises format writers, bundle layout, CLI helpers, core analysis,
loop detection, transcription helpers, worker availability, the GUI option bridge,
and ground-truth annotation parsing. It includes an Isophonics annotation tree for
the ground-truth matrix; real-audio evaluation is deliberately separate from the
ordinary test suite.

Once a complete local environment is available, the repository's configured quality
commands are:

```bash
uv run pytest
uv run ruff check .
uv run mypy
```

At the current revision, these commands are not a clean verification baseline in a
fresh checkout: the dependency declaration prevents normal test collection, and
the configured Ruff and mypy checks have existing findings. They are shown here as
the repository's intended commands, not as a claim of passing CI.

For an on-demand ground-truth run, the matrix accepts a music root and optional
artist/album limits:

```bash
python -m demixer.eval.groundtruth_matrix --music-root /path/to/music --limit 10
```

It requires the full analysis environment and real audio files; it is not an
offline performance or accuracy guarantee.

## Project status

This is experimental software. Its architecture is intentionally practical about
incompatible model stacks: heavier alternatives communicate through files and
subprocess workers rather than being forced into one fragile environment. The
trade-off is that worker provisioning, model availability, and output quality need
to be verified by the operator for each workflow.

## License

demixer is licensed under [AGPL-3.0-or-later](LICENSE). It integrates and can be
used alongside multiple third-party libraries, models, and reference annotations;
their licenses and distribution terms remain separate responsibilities.
