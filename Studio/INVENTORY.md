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
