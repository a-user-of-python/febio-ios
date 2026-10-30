# FEBio Studio iOS port — Phase A inventory

Facts read from the sources (not docs alone), 2026-10-28. This is the
plan of record for the port the user directed: the *real* FEBio Studio,
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
  path and is exactly the API the spike proved on the target iPad.
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
| File dialogs (QFileDialog everywhere) | Qt's iOS plugin backs QFileDialog with the native document picker (partial: single-file open/save OK, no directory picker). The user's signing setup has broken system pickers in other apps, so M1 does not depend on it (patch 0003 auto-opens the bundled sample). Milestone 3 switches to the proven app-folder pattern (app creates its folder under On My iPad; UIFileSharingEnabled is set in the iOS plist). |
| Drag & drop | Works inside the app via Qt; drops from other apps are limited on iOS. Not needed for M1. |
| Keyboard shortcuts | QAction/QShortcut fire from hardware-keyboard key events on iOS — expected to work with a hardware keyboard; verified in the keyboard+mouse milestone. |
| Mouse | Qt iOS delivers pointer events incl. right-click and wheel from mice/trackpads; `UIApplicationSupportsIndirectInputEvents` is set in the plist. Viewport orbit/pan/zoom is mouse-driven upstream (rhiSceneView mouse handlers) and works from touch-as-mouse in M1. |
| Touch | M1: taps act as clicks (Qt synthesizes mouse events from touch). Dedicated gestures (one-finger orbit, pinch zoom, two-finger pan, forgiving tap-to-select) are the viewport milestone — added in RHILib/rhiSceneView event handling, upstream of all tools, so every tool inherits them. |
| OpenGL context creation | None — QRhi creates the Metal device/swapchain (RhiWindow). |
| Fonts | Qt iOS uses the system font. Patch 0003 raises the app base font to 16 pt on iOS (font scaling only — no UI redesign, per the user's rule). |
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
and links for iOS arm64; The user can launch it, see the genuine main
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

## DEVICE FIX ROUND 2 — GREEN (2026-10-29)

Device verdict #2 on the fix-round-1 build: the tension block
loads ("success!" in the log, Objects (1) in the tree, block
visible) and the full load -> run -> results loop is
device-verified. New feedback: (A) the app renders squished at
a non-native size — the user wants it to treat the iPad like a
monitor at full native resolution; (B) a launch screen with
two controls — a "Launch FEBio" button and a gear-icon
settings button; (C) the settings must include a Display
Scaling control; (D) the left Model panel is vertically
squished (tree cut short, dead space below).

Fixes: 0018 (resolution diagnostics in the Log: screen pt /
DPR / native px / window pt / view px), 0019 (start screen +
gear settings + display scaling 75-175%, default 115%, in
QSettings, replacing 0014's hard-coded 1.15; showFullScreen
on iOS), 0020 (layout v2: left dock group takes the full
height the bottom dock leaves; Model panel tree gets 2/3 of
its internal split), and UIRequiresFullScreen added to
Studio/iOS/Info.plist.

Run **40910674041** (build-studio.yml, commit 4850c7d8)
succeeded on the standard macos-26 runner — job "FEBio Studio
unsigned IPA" completed/success. Artifact FEBioStudio-unsigned:
20,997,822 B zip / **21,035,344 B IPA, md5
f8a903fa7c64a0990447ca2f4fb33b26**, staged at
~/workspace/your_files/FEBioStudio-unsigned.ipa
(byte-identical, md5 verified after staging). Shipped-binary
checks: bundle com.user.febiostudio, arm64, UIRequiresFullScreen
= true in the bundled plist, and the new strings present in the
executable ("Launch FEBio", "displayScalePercent",
"Display Scaling", "iosLayoutVersion", the resolution-diagnostic
format strings). Note: every push also fires the legacy spike
workflow (build-ipa.yml); its run (40910674005) is NOT this
build — the Studio run is 40910674041.

Device verdict pending. The retest that matters: open app ->
start screen appears -> gear -> Display Scaling (set e.g.
140%) -> Save -> Launch FEBio -> Studio opens at the new
scale, block auto-loads, left Model panel full height, and
the Log shows the new "screen = ... / main window = ..."
lines (view px should equal native px) -> quit, reopen,
change scaling back to 115%, relaunch, confirm text size
changed.

Note: this section was appended locally after the code push
landed; it rides along with the next Studio/** push (a
doc-only push would trigger a redundant full rebuild).

## RC1 PUSH — gap-closure round (2026-10-29)

Commission: deep-dive audit for what's missing, add it,
get as close to releasable as possible, ship as GitHub Release
"rc1". The full audit lives in the goal workspace
(hidden_files/rc1-gap-ledger.md). What changed:

- **0003 (revised)** — auto-open sample is now **power-beam.feb**
  (50×8×8 mm cantilever; originally −10 mm tip displacement,
  20 steps — raised to −22 mm / 40 steps by the 0025 round, see
  below). The iOS block also **seeds the shared Documents
  folder** on launch (never overwriting user files): README.txt
  (what to copy in, which file types, the STEP note), plus
  copies of both sample models. tension-block.feb remains
  bundled and seeded.
- **0019 (revised)** — the launcher shows a version line:
  "FEBio Studio 3.2.0 - FEBio 4.13 - iOS port rc1".
- **0021** FEBioStudio.cpp + MainWindow.h + MainMenu.cpp +
  menuFile.cpp — iOS file access. (a) `AA_DontUseNativeDialogs`
  is set before the application object exists, so every
  QFileDialog in Studio (~60 call sites) is a Qt-widget dialog
  inside the app instead of the native document picker (which
  is unreliable under some signing setups). (b) File →
  **"Open from App Folder …"**: a list browser over Documents.
  **Open** routes through `CMainWindow::OpenFile` (the desktop
  dispatch); **Import Geometry** routes through
  `CMainWindow::ImportFiles` (the REGISTER_CLASS4 reader
  registry), so an imported mesh lands in the active model and
  goes through the normal mesh/material/BC → Run path. CAD
  extensions (step/stp/iges/igs/brep/brp) get an explicit
  "not in this build" message. The browser slot is compiled on
  all platforms (moc references it); only the menu action is
  iOS-only. Importer census (from the registry): feb, inp, k,
  dyn, stl, ply, obj, dxf, nas, unv, cdb, msh, byu, surf,
  hmascii, mphtxt, mesh, ele, elem, raw, pvo, vtk, vtu, vtp
  work; documents/results additionally fsm, fs2, fsprj, prv,
  xplt, pvd, vtm, fsps, n, key, log, txt.
- **0022** ModelTree.h/.cpp — the tree's context menu existed
  (contextMenuEvent) but no long touch ever delivered the
  event on iOS. iOS-only 450 ms press-and-hold timer
  (touch-source presses only; movement >14 px or release
  cancels) dispatches the event at the press point — the same
  pattern as the viewport's 0012 long-press.
- **0023** GLView.cpp — wheel classification: on iOS a Magic
  Keyboard trackpad reports as a non-synthesized wheel source
  *with* pixel deltas, so it took the mouse branch (step zoom)
  instead of panning. iOS-only: the discrete branch now also
  requires a null pixel delta; trackpads take the existing
  pixel-delta pan branch (Alt = zoom). Notched wheels are
  unchanged.
- **0024** menuHelp.cpp + menuPost.cpp — Help → About gains
  iOS-port lines (identification, attribution context, the
  headline limits). Post → Volume Render on iOS explains that
  it needs 3D textures the Metal backend doesn't provide,
  instead of silently adding a renderer that draws nothing
  (0011 made it crash-free; this makes it honest).
- **0025** PostDocument.cpp + FEBioStudio.cpp — rc1 device
  report: the power-beam results opened flat green. Root cause
  is upstream defaults, not the solve: on a fresh open the
  color map starts inactive with its data field unset ("(select)"
  in the Post panel) and the view opens on state 0, where
  displacement is genuinely zero, so the model renders as flat
  material color, undeformed. (The color range was never the
  problem: it defaults to RANGE_DYNAMIC, the displayed state's
  true min-max; the displacement map was likewise already
  active at its default scale of 1.0.) iOS-only, fresh opens
  only (no restored model data): if the opened results carry a
  displacement field - the same field the model deforms with -
  Initialize() selects its magnitude (component 6) in the
  color map, activates the color map, and opens on the last
  state. Defaults only: field, range, and state remain fully
  user-changeable, and every value shown is the solver's own.
  Second hunk: the two bundled samples are app-managed demo
  content, so a seeded sample whose bytes differ from the
  bundled copy is refreshed on launch (an upgrade that ships a
  new demo actually delivers it); user files and the README
  are never overwritten. Demo model raised at the same time
  (user request, "add more forces"): power-beam tip drop
  -10 mm -> -22 mm over 40 steps (44% of the 50 mm length);
  host-verified NORMAL TERMINATION, max displacement
  23.378 mm, max von Mises 2.179 (was 10.276 mm / 0.562).
- **0026** TimelineWidget.h/.cpp — device report: in the Post
  view only about the first 8 of the power-beam's 21 states
  were reachable; the timeline never scrubbed by touch.
  CTimelineWidget is custom-painted and implements only mouse
  handlers, and on this iOS build such widgets do not reliably
  receive synthesized mouse drags (the failure class behind
  0012/0017/0022). iOS-only: the widget now accepts touch
  events and handles them directly, mirroring the mouse
  semantics - a touch in the data area selects the closest
  state and a drag scrubs through all states; a drag on the
  range bar's slider (when shown) pans the visible window.
  Touches on the range-selector triangles are deliberately
  not claimed, so they keep the legacy path. Prev/next,
  first/last, the state spinbox, and playback are untouched.
- **0027** GLView.h/.cpp — forces-on-faces workflow audit:
  the add-load/BC chain (Physics menu + model-tree menus,
  CDlgAddPhysicsItem, Assign current selection, in-process
  run) is intact on iOS, but its first link was not: desktop
  selection is modifier-driven (Shift-click adds to the
  selection, Shift/Ctrl-drag rubber-band selects) and touch
  has no modifiers, so every tap replaced the selection and
  every one-finger drag orbited — a multi-face selection for
  a surface pressure, or a multi-node one for a nodal load,
  could not be built by touch at all. Two session toggles at
  the top of the viewport long-press menu (0012): "Add to
  Selection" (a touch tap selects with SELECT_ADD, like a
  Shift-click) and "Drag Selects Region" (a one-finger touch
  drag drives the existing rubber-band/region-select
  machinery instead of orbiting; a plain tap still
  click-selects). Only synthesized-touch presses are
  affected — mouse and trackpad keep desktop behaviour, and
  the transform (pivot) modes are untouched. The selection
  brush stays modifier-bound deliberately; region mode
  supersedes it for touch.
- **0030** MainWindow.cpp — device report (round 3): after
  a relaunch the layout "goes back" to the constructor's
  proportions — Build panel about half the width, Output
  about a third of the height, the 3D view a 464x267 pt
  strip on the 1180x820 pt screen (0018 Log line). Root
  cause: the 0016/0020 dock sizing ran ONCE, gated on
  iosLayoutVersion, and trusted the restored state after
  that — but the saved state's only writer is
  closeEvent -> writeSettings, which iOS's
  suspend-then-kill lifecycle does not reliably deliver,
  so relaunches restored a stale state or fell back to
  size-hint defaults. iOS-only: the sizing (left group
  16% / Build 17% of width, bottom group 12% of height,
  left group full remaining height, Model tree split
  2/3) now runs on EVERY launch, after restoreGeometry/
  restoreState, deferred until the window is full-screen
  (one settle retry if it is not), and the enforced
  geometry/state are written back to the MainWindow
  settings group so the next launch's restore starts
  from the same desktop-monitor proportions. In-session
  rearrangement still works as on desktop; a relaunch
  always returns to the enforced layout. No dock or
  feature removed — proportions only, both workspaces
  (the Model/Post panels share the one dock layout).
- **0032** PostLib/FESTLimport.h/.cpp — device report
  (2026-10-30): a Shapr3D-exported STL dropped into the app
  folder was rejected with "First line must be solid
  definition." Root cause is a dispatch split, not a missing
  reader: the app-folder dialog's "Open" button routes
  through CMainWindow::OpenFile, whose extension chain sends
  .stl to the POST reader (Post::FESTLimport) — and that
  reader is ASCII-only, upstream and here (its Load opens the
  file once in text mode and fails the first line). The
  geometry reader behind "Import Geometry" (MeshIO
  STLimport) already had an ASCII->binary fallback upstream
  and was never broken — host-verified. (Error-string
  forensics: errf appends, but FileReader::Open resets the
  error string, so a reader that retries shows only its last
  error; the single "First line" line in the device dialog
  is FESTLimport's fingerprint.) iOS-only: FESTLimport now
  tries a binary read first. Detection is SIZE-MATH-FIRST —
  the file is binary only if its size is exactly
  84 + 50 x (little-endian uint32 triangle count at offset
  80) — never by first word, because some binary headers
  legitimately start with "solid". On a size mismatch no
  error is recorded and the original ASCII path runs
  byte-identically, so ASCII files and malformed files
  behave (and fail) exactly as before. Host-verified by
  driving the real reader code: ASCII, binary with plain
  header, and binary with a "solid"-prefixed header all
  import to the same mesh (8 nodes / 12 elements for the
  test cube, no residual error string); a truncated binary
  and a garbage file fail cleanly with the legacy error.
- **0033** FEBioStudio/menuFile.cpp + MeshIO/ObjImport.cpp —
  device report (2026-10-30): "I can't import obj files."
  The OBJ importer was never missing: ObjImport is compiled
  in (globbed with MeshIO) and registered for "obj" in the
  CreateFileReader registry, it is listed in the 0021
  dialog, and its parser handles Shapr3D-flavoured OBJ
  (v/vt/vn lines, f v/vt/vn triples, multiple named
  objects/groups) — host-verified through the real
  ObjImport::Load (13 nodes / 18 faces on the test file).
  The break was the 0021 dialog itself: its "Open" button
  routes through CMainWindow::OpenFile, whose extension
  chain has NO route for registry-only geometry formats —
  it falls through and silently does nothing (double-click
  takes the same dead path). iOS-only: in
  on_actionAppFolder_triggered, the registry-only formats
  (obj, ply, dxf, nas, unv, cdb, msh, byu, surf, hmascii,
  mphtxt, mesh, ele, elem, raw, pvo) now route through
  ImportFiles for both buttons. Same patch, parser
  hardening found by the same host tests: OBJ's negative
  (relative) vertex indices were stored raw, producing
  out-of-range node ids in the built mesh; they are now
  converted to absolute indices against the vertices read
  so far, per the OBJ spec.
- **0034** Build script + Studio/TetGen/ — device report
  (2026-10-30): an imported part "has only 12 triangles"
  (a box skin: 2 triangles per flat face — geometrically
  correct) and, being a hollow surface with the port's
  TetGen/MMG switched off, could not be filled into a
  volume mesh for a solid run. The TetGen mesher class
  (MeshTools/FETetGenMesher) was present and registered
  all along, but without the TETLIBRARY compile definition
  its Apply() is a stub that returns 0. TetGen 1.5 sources
  (tetgen.h, tetgen.cxx, predicates.cxx — from the
  libigl/tetgen mirror of the official release;
  sha256 in the build ledger) are vendored in
  Studio/TetGen WITH their license: TetGen is AGPLv3.
  That is acceptable for this personal sideload build,
  but it is a real license change for the app binary and
  is recorded here deliberately — do not redistribute the
  app without honoring the AGPL. The build script now
  compiles libtet.a for iOS arm64 (predicates.cxx at -O0,
  as upstream's makefile prescribes for its exact
  arithmetic), passes USE_TETGEN=ON with TETGEN_INC /
  TETGEN_LIB_DIR to the Studio configure, and fails the
  build if TetGen's banner string is absent from the
  binary. Host-verified at the library level with the
  mesher's own switch construction: the 12-triangle cube
  skin tetrahedralizes to 6 tets / 8 points with total
  volume exactly 1.0 (unit cube), and with the mesher's
  element-size cap to 104 tets / 43 points, all volumes
  positive, all indices in range. MMG remains off.
- Patch chain 0001–0034 re-verified to apply in order to
  a pristine tree; the 0032/0033 results are byte-identical
  to the files exercised by the host reader harness.
- **App icon** — the port previously shipped NO iOS icon (only
  the desktop .icns). Original icon set (bending hex-mesh beam
  with a von Mises colormap, drawn for this port) in
  Studio/iOS/AppIcon/, wired via CFBundleIcons +
  CFBundleIcons~ipad and copied into the .app by the build
  script.
- **Build script** — bundles power-beam.feb + the icon PNGs,
  and now FAILS the build if UIFileSharingEnabled,
  LSSupportsOpeningDocumentsInPlace or UIRequiresFullScreen
  is not true in the *built* app's plist, or if the rc1
  feature strings ("power-beam.feb", "Open from App Folder",
  "iOS port rc1") are missing from the binary.
- Patch chain 0001–0028 + 0030 re-verified to apply in
  order to a pristine tree (MainWindow.cpp result
  byte-identical to the development tree). (0029 is the
  parallel states/export line, not yet landed.)

**Deliberately NOT in rc1** (full reasoning in the ledger):
STEP/IGES/BREP import + CAD meshing — Studio's CAD_FEATURES
couples OpenCASCADE *and* Netgen (importers are HAS_OCC stubs;
CAD meshing is Netgen's OCC module), neither has an iOS build
in this project, and an unmeshable import would not reach a
runnable model. Two-finger rotate sign — both paths use the
designed negative orbit factor; the residual uncertainty is
the QPA gesture-sign convention, which static analysis cannot
settle — left for a one-gesture device check rather than a
blind flip. Non-DEFAULT job configs, Python scripting, model
repository, FFmpeg export, ITK stacks, MMG/TetGen remeshing —
CMake-off/subprocess-bound, documented as limits in the repo
README and the in-app About.
