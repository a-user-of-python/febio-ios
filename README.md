# FEBio Studio for iPad

**The real [FEBio Studio](https://febio.org/febio-studio/) — the Qt desktop application — running natively on iPad, with the FEBio 4.13 solver built in.**

[![Build FEBio Studio for iOS](https://github.com/a-user-of-python/febio-ios/actions/workflows/build-studio.yml/badge.svg)](https://github.com/a-user-of-python/febio-ios/actions/workflows/build-studio.yml)
![Platform](https://img.shields.io/badge/platform-iPadOS%20(arm64)-blue)
![FEBio](https://img.shields.io/badge/FEBio-4.13-green)
![FEBio Studio](https://img.shields.io/badge/FEBio%20Studio-3.2.0-green)

This is not a reimplementation or a viewer. It is the actual FEBioStudio
source (pinned at 3.2.0) plus the FEBio solver SDK (4.13), cross-compiled
for iOS with Qt 6, adapted to iPadOS through a series of small, numbered
patches. The full loop works on device: **load a model → run the
simulation in-process → open the results (.xplt) and inspect them in the
Post view.**

> **rc1** is the first release candidate: an unsigned IPA attached to the
> GitHub release of the same name. Sideload it with your preferred tool.

## What works

- **The real Studio UI** — model tree, properties, graphics view, dialogs —
  at the iPad's native resolution, full screen.
- **Launch screen + settings** — a start screen with a display-scaling
  control (75–175%, persisted; implemented without `QT_SCALE_FACTOR`,
  which corrupts Studio's own geometry math).
- **In-process solving** — FEBio jobs run inside the app through the
  FEBio library (iOS forbids subprocesses); results open in the Post
  view with playback, data maps, and deformation.
- **Bring your own files** — the app exposes a folder in the Files app.
  Drop files in, then **File → Open from App Folder …** opens models and
  offers **Import Geometry** for mesh files — no native document picker
  involved. Importable in this build: `.stl .ply .obj .dxf .inp .k/.dyn
  .nas .unv .cdb .msh .byu .surf .hmascii .mphtxt .mesh .ele/.elem .raw
  .pvo .vtk .vtu .vtp`, plus `.feb` documents and `.xplt` results.
  Imported geometry follows Studio's normal mesh → material → BC → Run
  path. Job outputs land next to the model file, so results stay
  reachable in Files.
- **Bundled samples** — a bending cantilever beam (auto-opened: watch it
  bend 10 mm) and a tension block, also copied into the app folder on
  first launch.
- **Touch support** — tap-based selection and picking, a long-press
  context menu in the model tree, multi-touch orbit/pan/zoom, and
  trackpad scrolling classified correctly on Magic Keyboard.

## Honest limits

- **STEP / IGES / BREP import and CAD meshing are not in this build.**
  Studio couples those to OpenCASCADE **and** Netgen; neither CAD
  library has an iOS build here yet. The app says so plainly instead of
  failing silently — it's the top item for a future milestone. (Mesh
  formats above are the route for geometry in the meantime.)
- **Volume rendering** needs 3D textures the iOS Metal backend doesn't
  provide; the menu entry explains this instead of drawing nothing.
- **No subprocess anything**: external job configs (SSH/process),
  TetGen/MMG, FFmpeg export, Python scripting, and the online model
  repository are disabled or degrade gracefully.
- **Unsigned IPA** — you sideload it with your own signing.

## How it's built

- Upstream sources are **not** vendored here. CI clones FEBio and
  FEBioStudio at pinned commits and applies the numbered patch series in
  [`Studio/Patches/`](Studio/Patches/) — every iOS adaptation is a small,
  reviewable diff (see [`Studio/INVENTORY.md`](Studio/INVENTORY.md) for
  the full ledger).
- Qt is built for iOS from source (cached as a release artifact in a
  companion repo), FEBio is cross-compiled with its iOS CMake preset,
  and Studio links the FEBio solver as a library.
- Builds run on **free, standard GitHub-hosted runners** only
  (`build-studio.yml`). The IPA is produced unsigned; all file-sharing
  and feature strings are verified inside the built app before the
  artifact is uploaded.

## Repository layout

- `Studio/` — the iOS port: patches, build scripts, Info.plist, icons.
- `Model/` — bundled sample FEBio models.
- `Spike/` — the original feasibility spike (historical).
- `.github/workflows/` — `build-studio.yml` (the app) and `build-ipa.yml`
  (the legacy spike).

## Attribution & license

FEBio and FEBio Studio are developed by the Musculoskeletal Research
Laboratories at the University of Utah and the Musculoskeletal Biomechanics
Laboratory at Columbia University. This port is an independent,
unofficial adaptation; all FEBio/FEBioStudio code remains under its
original license — see [febio.org](https://febio.org) and the upstream
repositories ([FEBio](https://github.com/febiosoftware/FEBio),
[FEBioStudio](https://github.com/febiosoftware/FEBioStudio)).

If you use FEBio in research, please cite it as requested by the FEBio
project.
