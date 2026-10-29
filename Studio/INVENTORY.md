# FEBio Studio iOS port — Phase A inventory

Facts read from the sources (not docs alone), 2026-10-28. This is the
plan of record for the port Sean directed: the *real* FEBio Studio,
Qt and all, functioning and looking like the desktop program, plus
touch support — maximum reuse, minimum reimplementation.

## Pinned versions

| Component | Version | Commit | Source |
|---|---|---|---|
| FEBio Studio | **3.2.0** (`FBS_VERSION 3.2.0`, FEBioStudio/version.h) | `68380947421350c9a7dcb592f282a882fcbad02b2` (2026-08-11) | github.com/febiosoftware/FEBioStudio |
| FEBio SDK (for Studio) | **4.13.0 release** | tag `v4.13` = `32ae206ff4881dfb54f62296cd1558e58ed9fcc6` | github.com/febiosoftware/FEBio |
| FEBio (spike only) | 4.13.0 develop snapshot | `9605327359ded64ea0d65dd1aeca484fc45a9acd` (2026-10-27) | github.com/febiosoftware/FEBio |

- Studio builds against the **FEBio SDK** (`find_package(FEBio
  REQUIRED)`). First attempt used the spike's develop pin and
  failed exactly on API drift (run 40772868459): Studio's
  FSCore/Archive.h calls `vec2d::x()/y()`, accessors FEBio develop
  removed in commit `15edba277c` (2026-05-19, "Modified vec2d
  class to be more consistent with other vector classes"). The
  v4.13 **release tag** predates that change and still has the
  accessors (verified via the GitHub API), so the Studio build
  pins the release SDK — the pairing upstream ships. The spike
  keeps its develop pin (device-verified; it does not use the
  changed API).
- Both are MIT-licensed. Patches are legal; every patch is
  enumerated in `Studio/Patches/` with its reason.

## Build system and module map

- CMake ≥ 3.15, C++17, AUTOMOC/AUTORCC on. Sources are globbed per
  directory (`findHdrSrc`), so the file list is the directory list.
- One app target (`FEBioStudio`) + 25 libraries:
  Abaqus, Ansys, Comsol, CUILib, FEBio (Studio-internal), FEMLib,
  FSCore, GeomLib, GLLib, GLWLib, RTLib, ImageLib, LSDyna, MeshIO,
  MeshLib, MeshTools, Nike3D, PostGL, PostLib, XPLTLib, FEBioLink,
  FEBioRun, FEBioMonitor, VTKLib, PyLib, RHILib.
  ≈740 .cpp files total; the app directory alone has 301.
- Qt discovery in the root CMakeLists is skipped when `Qt6_DIR` and
  `CMAKE_PREFIX_PATH` are preset — the iOS build presets both.
- FEBio linkage: `FEBioConfig.cmake` ships in the FEBio tree and
  supports in-tree use (`FEBio_DIR` = FEBio source root). The
  v4.13 tag's config is older than develop's: no FEBio_BUILD_DIR
  support — it looks for the libraries under `<source>/build/lib`,
  so the SDK build tree lives inside the source tree
  (run 40777591066's configure failure; fixed by building there).
  No SDK install step needed. Targets consumed: FEBio::FECore (everything),
  FEBio::FEBioLib/FEBioFluid/FEBioMech/FEBioMix (FEBioRun,
  FEBioLink), FEBio::FEBioXML/FEBioPlot/FEAMR (app),
  FEBio::FEBioOpt (ImageLib), FEBio::FEImgLib.
- Because FEBio is linked **statically**, its self-registration
  (static factory objects in every module library) would be partly
  dropped by the linker. The spike solved this with `-force_load`
  per FEBio archive; the Studio build does the same (build-script
  level, listed in the script header — no source patch).
- Optional features switched OFF for iOS (all upstream CMake
  options): USE_MMG, USE_TETGEN, CAD_FEATURES (Open CASCADE +
  NetGen), USE_SSH (+OpenSSL), MODEL_REPO (libzip + SQLite),
  USE_FFMPEG, USE_PYTHON, USE_ITK (SimpleITK). BUILD_UPDATER and
  BUILD_TESTS are already OFF by default. These remove features
  (tet remeshing, CAD import, remote jobs, the model repository,
  video export, Python plugins, image stacks), not core modelling,
  meshing, solving, or post-processing. They can be revisited one
  by one after the core port stands.

## Solver execution — the subprocess audit

Launch configurations (`CLaunchConfig`): DEFAULT, LOCAL, REMOTE,
PBS, SLURM, CUSTOM.

- **DEFAULT = in-process.** `CFEBioJobManager::startDefaultJob`
  starts `CFEBioJobThread` (a QThread) → `FEBioRun` → FEBioLib
  `febio::SolveModel` in the app process. This is the standard Run
  path and is exactly the API the spike proved on Sean's iPad.
  iOS-safe.
- **LOCAL = subprocess.** `CLocalJobProcess` (QProcess) spawns an
  external febio executable. Cannot work on iOS (no subprocesses).
  It is an opt-in config a user must deliberately create/select;
  disabling it on iOS is a later-milestone patch.
- **REMOTE / PBS / SLURM / CUSTOM** = SSH-based remote jobs
  (`CRemoteJob`). Unusable on iOS; USE_SSH=OFF already removes the
  library dependency.
- FEBio **plugin loading from the config file is already disabled
  by Studio itself** (`config.readPlugins = false`,
  FEBioRun/FEBioInit.cpp) — no dlopen gap at startup.
- Other QProcess uses: the Updater (not built), batch conversion
  via an external program (same class as LOCAL), and "open
  externally" helpers (may no-op on iOS; cosmetic).

## The 3D viewport — the GL question (much smaller than feared)

- All scene drawing goes through the **GLRenderEngine** abstract
  interface (GLLib). Its implementations are `rhiRenderer`
  (QRhi), `GLMeshBuilder` (CPU mesh building) and `RayTracer`
  (CPU, RTLib). No scene code touches OpenGL directly.
- The app view is `CGLView : rhiSceneView : RhiWindow` (a QWindow),
  embedded into the Widgets UI with
  `QWidget::createWindowContainer` (FEBioStudio/GLViewer.cpp).
  It uses the QRhi **private** API (`<rhi/qrhi.h>`), hence
  Qt6::GuiPrivate on the app and RHILib targets.
- **Raw OpenGL in the whole Studio tree: effectively zero live
  calls.** No glGenBuffers / glDrawArrays / shader calls anywhere;
  no GLEW includes at all (BUILD.md's GLEW requirement is stale).
  The only glBegin/glEnd in the tree (MeshTools/GSketch.cpp) sits
  inside a block comment — dead code. The legacy desktop-GL render
  engine no longer exists in this vintage. *There is no
  fixed-function GL problem to solve.*
- Shaders: 9 GLSL pairs in RHILib/shaders, baked by
  `qt_add_shaders` (host `qsb` from the desktop Qt kit via
  QT_HOST_PATH).
- Backend choice: `RhiWindow::InitRHI` implements OpenGLES2,
  Vulkan, D3D11/12 and **Metal** (the Metal branch is compiled for
  `Q_OS_MACOS || Q_OS_IOS`). BUT `CMainWindow::MapToValidAPI`
  currently forces OpenGLES2 on Apple platforms — upstream
  commented out Metal with "TODO: Restore this when 3D textures
  are working on Metal". Port decision (**patch 0002**): on iOS
  only, force QRhi::Metal — the native backend (Qt's iOS kit has
  no ANGLE), and the mesh viewport does not depend on the
  3D-texture path (that is volume/image rendering). Fallback if
  the device viewport misbehaves: flip that one line back to
  OpenGLES2 (QRhi over EAGL ES 3).
- `find_package(OpenGL REQUIRED)` in FindDependencies.cmake is
  vestigial (nothing links the CMake OpenGL targets) but fails
  under an iOS sysroot → **patch 0001** guards it off on iOS.

## Qt for iOS route

- Requirement (BUILD.md): Qt ≥ 6.5, 6.8 recommended. Upstream's
  own macOS CI pins **Qt 6.9.3** (ci/macOS/postBuild.sh). The
  QRhi private headers are version-sensitive, so the port uses
  upstream's pin: **Qt 6.9.3** (script falls back to 6.8.3 if the
  6.9.3 archives are unavailable).
- Required Qt components (FindDependencies.cmake):
  **Widgets, Gui, Network, OpenGL, OpenGLWidgets, ShaderTools**,
  plus **GuiPrivate**. All ship in Qt's official iOS kit
  (OpenGL/OpenGLWidgets are part of qtbase and are built for iOS;
  ShaderTools is its own module, included in the full kit).
  Qt Charts is mentioned in BUILD.md but **not referenced by this
  vintage's CMake or sources** (grep-verified) — not needed.
- Install method on the macos-26 runner: **aqtinstall**
  (`pip install aqtinstall`), two kits into one prefix —
  `mac desktop 6.9.3 clang_64` (host tools: moc, rcc, qsb) and
  `mac ios 6.9.3 ios` (the iOS kit). Qt's own toolchain file
  (`<ios-kit>/lib/cmake/Qt6/qt.toolchain.cmake`) +
  `-DQT_HOST_PATH=<desktop kit>` is the supported cross setup.
  Qt for iOS is static: no frameworks to embed, platform plugin
  (QIOSIntegration) links statically. The build script verifies
  the plugin actually made it into the binary (strings check) —
  a missing platform plugin is the one failure CI can catch
  before the device does.

## Platform gaps → planned iOS mapping

| Desktop facility | iOS mapping |
|---|---|
| File dialogs (QFileDialog everywhere) | Qt's iOS plugin backs QFileDialog with the native document picker (partial: single-file open/save OK, no directory picker). Sean's signing setup has broken system pickers in other apps, so M1 does not depend on it (patch 0003 auto-opens the bundled sample). Milestone 3 switches to the proven app-folder pattern (app creates its folder under On My iPad; UIFileSharingEnabled is set in the iOS plist). |
| Drag & drop | Works inside the app via Qt; drops from other apps are limited on iOS. Not needed for M1. |
| Keyboard shortcuts | QAction/QShortcut fire from hardware-keyboard key events on iOS — expected to work with Sean's keyboard; verified in the keyboard+mouse milestone. |
| Mouse | Qt iOS delivers pointer events incl. right-click and wheel from mice/trackpads; `UIApplicationSupportsIndirectInputEvents` is set in the plist. Viewport orbit/pan/zoom is mouse-driven upstream (rhiSceneView mouse handlers) and works from touch-as-mouse in M1. |
| Touch | M1: taps act as clicks (Qt synthesizes mouse events from touch). Dedicated gestures (one-finger orbit, pinch zoom, two-finger pan, forgiving tap-to-select) are the viewport milestone — added in RHILib/rhiSceneView event handling, upstream of all tools, so every tool inherits them. |
| OpenGL context creation | None — QRhi creates the Metal device/swapchain (RhiWindow). |
| Fonts | Qt iOS uses the system font. Patch 0003 raises the app base font to 16 pt on iOS (font scaling only — no UI redesign, per Sean's rule). |
| Clipboard | QClipboard works on iOS for text. |
| Settings (QSettings) | Works (app-container plist). First launch uses defaults; the settings dialog is upstream UI. |
| Splash screen | A pixmap QSplashScreen — plain widget, works. |
| Multiple windows | Studio is one QMainWindow with docks/tabs — maps to the single iOS window. Detachable docks may stay attached; acceptable for M1. |
| Update checker | Does a network version check at startup (Qt Network). Left as-is for M1; disabled by a patch if it shows UI on first launch. |
| Printing (QPrinter) | Not used in this vintage's app sources (grep-verified). |
| Web views (QWebEngine) | Not used (grep-verified) — good, WebEngine has no iOS build. |

## Milestone 1 build recipe (CI, standard macos-26 runner)

1. aqtinstall: Qt 6.9.3 desktop (host tools) + iOS kit.
2. FEBio v4.13 release @ tag pin → static iOS libraries via
   `Studio/Scripts/build-febio-sdk-ios.sh` (the spike's proven
   toolchain and patches, separate build tree).
3. FEBio Studio @ pin (codeload tar.gz) → apply Studio patches
   0001–0005 → CMake (Qt iOS toolchain, QT_HOST_PATH, FEBio_DIR
   at the in-tree SDK, all optional features OFF,
   SET_DEVCOMMIT=OFF, deployment target 17.0, omp shim include
   path reused from the spike) → Ninja build.
   `-force_load` for every FEBio archive at the app link
   (patch 0005, target-scoped — global linker flags would also
   hit CMake's compiler test programs and break configure; that
   was run 40760342892's failure, fixed by 0005).
4. Copy `Model/tension-block.feb` into the .app; compile the
   launch-screen storyboard with ibtool and copy it in; verify
   arm64 + QIOS plugin strings; package the unsigned IPA
   (Payload zip), artifact name **FEBioStudio-unsigned**.

## Studio patches (all in Studio/Patches/, applied to the pin)

- **0001** FindDependencies.cmake — skip `find_package(OpenGL
  REQUIRED)` on iOS (vestigial; would fail under the iOS sysroot).
- **0002** FEBioStudio/MainWindow.cpp — on iOS, MapToValidAPI
  returns QRhi::Metal (see viewport section). macOS unchanged.
- **0003** FEBioStudio/FEBioStudio.cpp — iOS only: 16 pt base font;
  on launch with no file argument, copy the bundled
  tension-block.feb to Documents and open it via the same
  `CMainWindow::OpenFile` entry point the desktop build uses for
  command-line files.
- **0004** CMakeLists.txt — on iOS use `iOS/Info.plist` (provided
  by Studio/iOS/ in this repo: bundle id com.user.febiostudio,
  iPad device family, orientations, launch storyboard, file
  sharing on) instead of the macOS plist.
- **0005** CMakeLists.txt — on iOS, `-force_load` every FEBio
  archive into the app target (static-registration survival) and
  link `-framework Accelerate` (NumCore's Apple sparse solvers;
  the imported FEBio targets do not propagate it).
- **0006** CMakeLists.txt — deployment target: the APPLE block's
  hardcoded 10.15 (a macOS floor) becomes
  -miphoneos-version-min < 13 on iOS, where Qt 6.9's
  std::filesystem declarations are unavailable
  (run 40781530344). iOS gets 17.0; macOS unchanged.
- **0007** FEBioStudio/iOSQProcess.h (new) + includes in six
  headers — iOS has no QProcess (QT_CONFIG(process) off; the
  header declares nothing), but Studio uses
  QProcess::ExitStatus/ProcessError in signal/slot signatures,
  including the DEFAULT in-process job path
  (run 40785251568). The new header is an iOS-only minimal
  QProcess stand-in: enums + the small called-method surface;
  start() is a no-op and the state stays NotRunning, so
  process-spawning features (LOCAL jobs, batch, plugin builds,
  updater) degrade to "could not start" on iOS. Desktop builds
  see an empty header.
- **0008** CMakeLists.txt + PyLib/PythonRunner.cpp — no CPython
  exists on iOS, but PyLib's sources include pybind11
  unconditionally (run 40789177730). On iOS the PyFBS*.cpp
  module-registration sources are filtered out of PyLib (their
  only caller is PythonRunner) and PythonRunner's implementation
  is replaced by an interface-identical stub whose runScript
  reports failure immediately. The Python editor window still
  opens; scripting itself is unavailable on iOS.
- **0009** FEBioStudio/iOSOmpStub.c (new) + CMakeLists.txt —
  the final link failed on seven omp_* symbols
  (run 40795656325): the iOS SDK has no OpenMP runtime, but
  FEBio's FEContactPotential and Studio's GLLib/RTLib call the
  API explicitly. The stub is the spike's device-verified
  single-threaded omp_stub.c, added to the app target.
- **0010** CMakeLists.txt — 16 duplicate symbols at the app
  link (run 40798904142): Studio vendors copies of FEBio's
  QuadricFit/FENNQuery sources and both sides define a free
  fact(int); force-loading every FEBio archive makes the
  duplicates collide (on desktop FEBio links shared, so they
  never do; the modern linker ignores -multiply_defined —
  run 40802041535). Resolved by renaming the Studio-side
  symbols in the only targets that touch them: QuadricFit →
  QuadricFitFBS (MeshTools + app; Studio's copy has an extra
  Fit() overload the app needs, FEBio's serves FEBioMech),
  cmp_node → cmp_node_fbs (MeshTools), fact → fact_fbs
  (ImageLib).
- **0011** RHILib/rhiTexture.cpp + rhiVolumeRenderPass.cpp —
  3D-texture volume rendering is the one feature Metal cannot
  do the desktop way (the reason upstream's Metal line is
  commented out). Previously an unsupported format hit an
  assert and callers built shader resources around a null
  texture (crash path). Now: Texture3D::create leaves the
  texture null, setTexture3D treats null as "volume rendering
  unavailable" and returns, upload is validity-guarded, and
  draw() already skipped texture-less passes — a clean
  feature-disable on any backend without 3D textures. Core
  mesh/post rendering never uses 3D textures.
- **0012** FEBioStudio/GLView.h/.cpp — touch input (M2). The
  viewport is a QWindow, so this is QTouchEvent, not QWidget
  gestures. One finger is NOT claimed: Qt's synthesized mouse
  events keep driving orbit/tap-select identically to desktop.
  The patch adds: a touchEvent override (two-point state →
  centroid pan with the middle-drag formula, pinch Zoom with
  the native-gesture call, two-finger in-plane Orbit);
  m_touchMulti, which makes mouseReleaseEvent ignore the
  synthesized release that ends a claimed gesture (without it,
  every pinch ends as a click-select or a spurious undoable
  view change — the transition trap in the touch-mapping
  report); a 450 ms long-press timer → the same
  BuildContextMenu QMenu the right-button branch builds;
  source-dependent click deadzone (3 px mouse / 14 px touch);
  SelectPivot refresh on synthesized presses (pivot mode is
  otherwise hover-set and stale for touch); pick-source
  tracking for 0013; GVContextMenu row height 25 → 34 on iOS.
  Flags are cleared only by the touch layer (TouchEnd/Cancel);
  the gesture commits as ONE CCmdChangeView using the
  press-time m_oldCam, like the mouse path.
- **0013** FEBioStudio/GLViewSelector.cpp — pick tolerance:
  all nine `S = 4`/`S = 6` half-extents scale by
  CGLView::PickToleranceScale() (1 mouse / 3 touch, via the
  existing m_glv pointer; the one file-local free function
  takes it as a parameter). No signature changes to the
  Select* entry points.
- **0014** FEBioStudio/FEBioStudio.cpp — vision scaling per
  the touch-mapping report: platform font scale (replacing
  0003's fixed 16 pt) + a short iOS-only stylesheet
  (tree/list item min-height 30 px, button/tab padding).
  QT_SCALE_FACTOR deliberately not used — it would scale the
  viewport's logical coordinates and corrupt picking math.
  REVISED in the device fix round (2026-10-29): the first
  device pass found ×1.3 too big — scale is now ×1.15 and the
  button/tab vertical padding is halved (6 px → 3 px); the
  30 px item min-height (touch minimum) is unchanged.
- **0015** FEBio/FEBioFormat.cpp — importer fix: guard
  ParseLogfileSection against leaf tags. A childless
  `<logfile/>` is a single self-contained token in FECore's
  XMLReader stream (no end tag follows it), but the function
  advanced unconditionally and looped to an end tag that
  never comes, running off the end of the file — the device
  failure "FATAL ERROR: Unexpected end of file (line 202)"
  that killed the built-in model's load. The sibling
  ParsePlotfileSection already had this guard. Reproduced
  and verified on the host against the real XMLReader: the
  unpatched control flow throws exactly the device error;
  with the guard the Output section parses and the import
  loop ends at </febio_spec>. (The FEBio solver reads the
  same file fine — it uses a different reader; the bundled
  .feb in the IPA is byte-identical to Model/tension-block.feb.)
- **0016** FEBioStudio/MainWindow.cpp — iOS layout
  proportions: the desktop first-launch proportions left the
  3D view ~40% × 35% of the iPad screen. In readSettings,
  once per layout version (versioned settings key, so it
  also applies over an upgraded install), deferred-size the
  docks from the actual window size: left ≈16% and right
  ≈17% of width, output ≈12% of height; the document view
  takes the rest. Users can rearrange afterwards as on
  desktop; their saved layout is kept.
- **0017** FEBioStudio/CreatePanel.cpp — iOS create flow:
  on desktop, tapping a shape icon only activates its
  parameter pane; the object is added by a separate Create
  button in the toolbox's Parameters section, below the
  icon grid inside the panel's scroll area — off-screen in
  the iPad's Build panel, so taps on shapes appeared to do
  nothing (the buttons are plain QToolButtons and did
  receive the taps). On iOS, selecting a primitive
  (CDefaultCreatePane) now also creates the object with the
  pane's default parameters: one tap adds the shape. Panes
  needing viewport input (springs, curves, lofts) keep the
  desktop flow.
- **0018** FEBioStudio/GLView.cpp — resolution diagnostics
  (device fix round 2, item A): CGLView::customInit already logs
  backend/driver/sample count to the app Log; a deferred entry
  now adds the screen size (points), devicePixelRatio, the
  computed native pixel size, the main-window and view-window
  sizes (points), and the swapchain's surfacePixelSize — the
  numbers that prove whether the app runs at the panel's native
  resolution (view px == native px) or is handed a scaled screen.
- **0019** FEBioStudio/FEBioStudio.cpp — start screen + display
  scaling (device fix round 2, items B and C). An iOS-only
  pre-main-window start screen in main(): a title and exactly
  two controls — a "Launch FEBio" button and a gear-icon button
  beside it (the gear is painted at runtime; Studio's resources
  have no settings artwork). The gear opens a Settings dialog
  whose control is **Display Scaling**: slider + spinbox,
  75–175%, persisted in the same QSettings store the main
  window uses (IniFormat/UserScope, MRLSoftware/FEBioStudio,
  group "iOS", key "displayScalePercent"; default **115** — the
  value the first device pass settled on, now user-adjustable).
  The patch-0014 mechanism (platform font scale + stylesheet)
  is driven by the stored value; application always scales from
  the pristine platform font, so re-applying after a settings
  change cannot compound; row min-height keeps 0014's 30 px as
  a floor and grows with the scale. Patch 0014 itself is NOT
  edited (its block is replaced in main by the launcher call).
  Same patch: on iOS the main window is shown with
  showFullScreen() (item A), so any restored desktop geometry
  cannot shrink it below the full native display. Launching
  proceeds through the unchanged flow (splash, main window,
  sample auto-open).
- **0020** FEBioStudio/MainWindow.cpp — layout version 2
  (device fix round 2, item D): the 0016 pass sized dock widths
  and the bottom dock only, and the left tab group
  (Project/Model/Post/Monitor, tabified into one left-area
  group) ended mid-height at the restored proportions — the
  model tree was cut short with dead space below. The pass now
  also resizeDocks the left group vertically to the height the
  bottom dock leaves, and inside the Model panel raises the
  tree's share of its internal vertical splitter (tree stack :
  properties = 2:1, stretch factors set so resizes keep
  favouring the tree). Versioned key bumped to 2, so it fires
  once on upgraded installs; user layouts persist afterwards.
  Also: `Studio/iOS/Info.plist` (this repo's file, not a Studio
  patch) gains **UIRequiresFullScreen** — the app always owns
  the full native display on iPad, the way the desktop build
  owns a monitor (item A).


## M2 BUILD — GREEN (2026-10-29)

Run **40812061278** succeeded with patches 0011–0014 applied
(3D-texture clean disable, CGLView touch input, touch pick
tolerance, vision scaling). Artifact `FEBioStudio-unsigned`:
20,994,923 B zip / 21,027,897 B IPA, staged at
~/workspace/your_files/FEBioStudio-unsigned.ipa (supersedes
the M1 IPA at the same path). Device verdict pending: the
checks that matter are (1) main window + auto-opened model +
mesh visible (Metal viewport), (2) one-finger orbit + tap
select with the larger tolerances, (3) pinch / two-finger pan
/ rotate without selection corruption, (4) long-press context
menu, (5) Run a solve from the real UI (DEFAULT launch config,
in-process). Conditional item from the touch-mapping report,
deliberately NOT patched yet: ModelTree long-press (patch only
if the device shows the iOS QPA does not deliver context-menu
events for long touches on the tree).

## M1 RESULT — GREEN (2026-10-29)

Run **40808198705** succeeded on the standard macos-26 runner:
all 890 Ninja steps (25 Studio libs + the full app) compiled and
linked for iOS arm64; CI verify confirmed the Qt iOS platform
plugin is linked and FEBio material registration is present in
the binary. Artifact `FEBioStudio-unsigned`: 20,994,331 B zip /
21,026,489 B IPA (52,310,536 B arm64 executable inside), bundle
com.user.febiostudio, tension-block.feb bundled, launch
storyboard compiled in, file sharing enabled. Staged at
~/workspace/your_files/FEBioStudio-unsigned.ipa. Device verdict
pending — see "What M1 will and won't prove" below for what the
first launch does and does not establish.

## What M1 will and won't prove

Will: the real Studio binary (all 25 libs + app) cross-compiles
and links for iOS arm64; Sean can launch it, see the genuine main
window (menus, model tree, docks, viewport), and the bundled
tension-block model opens in it.

Won't (yet): whether the QRhi/Metal viewport draws the mesh on
his iPad (first device run decides; GLES fallback is one line);
solving from the UI (milestone 2 — the in-process path is proven,
the UI path is not); opening arbitrary files (milestone 3);
touch gestures beyond tap-as-click (viewport milestone).

## DEVICE FIX ROUND 1 — GREEN (2026-10-29)

Device verdict #1 on the M2 build (iPad Air M3): the app
launches, Metal backend confirmed in the log, viewport draws
(grid + triad) — but (1) the built-in model failed to load
("FATAL ERROR: Unexpected end of file (line 202)"), (2) the
UI was "a bit big", (3) Build > Create shape icons appeared
unresponsive, (4) the 3D view was a small centre window in
desktop layout proportions.

Fixes: 0014 revised (vision scale x1.15, halved vertical
padding), 0015 (importer childless-<logfile/> guard — the
load failure's root cause, host-proven against the real
XMLReader), 0016 (iPad layout proportions: docks sized from
the actual window, viewport dominant), 0017 (iOS tap on a
primitive icon also creates the object). Patch chain
0001-0017 verified to apply in order to a pristine tree.

Run **40858059701** succeeded (job 123393974992 completed
success; the run-level status endpoint briefly reported a
stale "completed" before the job had actually finished —
job status + artifact presence are the trustworthy signals).
Artifact `FEBioStudio-unsigned`: 20,996,639 B zip /
21,028,374 B IPA, md5 dbc0cf43f3e4c2a27c93b33256441c99,
staged at ~/workspace/your_files/FEBioStudio-unsigned.ipa
(supersedes the M2 IPA). The .feb inside this IPA is again
byte-identical to Model/tension-block.feb (md5
2495391f22dfaf43d6ccf6d4be008430). Device verdict pending:
launch -> block visible in a now-dominant 3D view ->
orbit/select/pinch/long-press -> tap a Create shape -> it
appears -> FEBio menu Run -> results colour the block ->
and whether the size is comfortable now.

Note: this section was appended locally after the code push
landed; it rides along with the next Studio/** push (a
doc-only push would trigger a redundant full rebuild).
