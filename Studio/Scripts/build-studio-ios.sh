#!/bin/bash
# Cross-compile the REAL FEBio Studio 3.2.0 for iOS arm64 (unsigned).
#
# Pipeline (see Studio/INVENTORY.md for the reasoning):
#   1. Install Qt (aqtinstall): desktop kit for host tools (moc, rcc,
#      qsb) + the iOS kit. Upstream's own macOS CI pins Qt 6.9.3;
#      fall back to 6.8.3 (BUILD.md's recommendation) if needed.
#   2. Build the FEBio solver static libraries with the spike's
#      proven script (Scripts/build-febio-ios.sh).
#   3. Fetch FEBio Studio at the pinned commit (codeload tar.gz),
#      apply the enumerated patches in Studio/Patches/, configure
#      with Qt's iOS toolchain against the in-tree FEBio SDK, build.
#   4. Bundle the spike's reference model, compile the launch
#      storyboard, sanity-check the binary (arm64, Qt iOS platform
#      plugin linked), package the unsigned IPA.
#
# Link note: FEBio registers its materials/models through static
# factory objects. With static libraries the linker would drop
# unreferenced archives, so every FEBio archive is -force_load'ed
# into the app (same solution as the spike, which is
# device-verified).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STUDIO_COMMIT="68380947421350c9a7dcb592f282a882fcbad02b2"
WORK="$ROOT/build/studio"
SRC="$WORK/src"
BLD="$WORK/build"
QT_ROOT="$WORK/Qt"
mkdir -p "$WORK"

NCPU="$(sysctl -n hw.ncpu)"

# ---------------------------------------------------------------- Qt
echo "== installing Qt (aqtinstall)"
python3 -m pip install --quiet --break-system-packages aqtinstall
QT_VERSION=""
for v in 6.9.3 6.8.3; do
	echo "-- trying Qt $v"
	if python3 -m aqt install-qt mac desktop "$v" clang_64 -O "$QT_ROOT" \
	   && python3 -m aqt install-qt mac ios "$v" ios -O "$QT_ROOT"; then
		QT_VERSION="$v"
		break
	fi
	echo "-- Qt $v install failed, trying next candidate"
done
if [ -z "$QT_VERSION" ]; then
	echo "ERROR: could not install any candidate Qt version" >&2
	exit 1
fi
QT_DESKTOP="$QT_ROOT/$QT_VERSION/clang_64"
QT_IOS="$QT_ROOT/$QT_VERSION/ios"
echo "== Qt $QT_VERSION ready (host: $QT_DESKTOP, ios: $QT_IOS)"
test -f "$QT_IOS/lib/cmake/Qt6/qt.toolchain.cmake"

command -v ninja >/dev/null || brew install ninja

# ------------------------------------------------------------- FEBio
echo "== building FEBio solver (spike script)"
bash "$ROOT/Scripts/build-febio-ios.sh"
FEBIO_SRC="$ROOT/build/febio/src"
FEBIO_BLD="$ROOT/build/febio/build"
FEBIO_LIB="$ROOT/build/febio/lib"

# ---------------------------------------------------- FEBio Studio
if [ ! -f "$WORK/.studio-src.stamp" ]; then
	echo "== fetching FEBio Studio @ $STUDIO_COMMIT (codeload archive)"
	rm -rf "$SRC" "$WORK/FEBioStudio-$STUDIO_COMMIT" "$WORK/studio.tar.gz"
	curl -sfL -o "$WORK/studio.tar.gz" "https://codeload.github.com/febiosoftware/FEBioStudio/tar.gz/$STUDIO_COMMIT"
	tar -xzf "$WORK/studio.tar.gz" -C "$WORK"
	mkdir -p "$SRC"
	cp -R "$WORK/FEBioStudio-$STUDIO_COMMIT/." "$SRC/"
	rm -rf "$WORK/FEBioStudio-$STUDIO_COMMIT" "$WORK/studio.tar.gz"
	git -C "$SRC" init -q  # so `git apply` behaves for Studio/Patches/
	touch "$WORK/.studio-src.stamp"
fi

echo "== applying Studio patches"
for p in "$ROOT"/Studio/Patches/*.patch; do
	name="$(basename "$p")"
	if git -C "$SRC" apply --check "$p" 2>/dev/null; then
		git -C "$SRC" apply "$p"
		echo "   applied $name"
	elif git -C "$SRC" apply --reverse --check "$p" 2>/dev/null; then
		echo "   already applied $name"
	else
		echo "   ERROR: $name does not apply" >&2
		exit 1
	fi
done

# iOS bundle resources the CMake patch (0004) points at.
mkdir -p "$SRC/iOS"
cp "$ROOT/Studio/iOS/Info.plist" "$SRC/iOS/Info.plist"

# ---------------------------------------------------------- configure
FORCE_LOADS=""
for a in "$FEBIO_LIB"/*.a; do
	FORCE_LOADS="$FORCE_LOADS -Wl,-force_load,$a"
done

echo "== configuring FEBio Studio for iOS arm64"
cmake -S "$SRC" -B "$BLD" -G Ninja \
	-DCMAKE_TOOLCHAIN_FILE="$QT_IOS/lib/cmake/Qt6/qt.toolchain.cmake" \
	-DQT_HOST_PATH="$QT_DESKTOP" \
	-DCMAKE_PREFIX_PATH="$QT_IOS" \
	-DQt6_DIR="$QT_IOS/lib/cmake/Qt6" \
	-DQt_Root="$QT_ROOT/$QT_VERSION" \
	-DFEBio_DIR="$FEBIO_SRC" \
	-DFEBio_BUILD_DIR="$FEBIO_BLD" \
	-DCMAKE_BUILD_TYPE=Release \
	-DCMAKE_OSX_DEPLOYMENT_TARGET=17.0 \
	-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH \
	-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=BOTH \
	-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=BOTH \
	-DSET_DEVCOMMIT=OFF \
	-DUSE_MMG=OFF \
	-DUSE_TETGEN=OFF \
	-DCAD_FEATURES=OFF \
	-DUSE_SSH=OFF \
	-DMODEL_REPO=OFF \
	-DUSE_FFMPEG=OFF \
	-DUSE_PYTHON=OFF \
	-DUSE_ITK=OFF \
	-DBUILD_UPDATER=OFF \
	-DBUILD_TESTS=OFF \
	-DCMAKE_C_FLAGS="-I$ROOT/Scripts/ios-shim" \
	-DCMAKE_CXX_FLAGS="-I$ROOT/Scripts/ios-shim" \
	-DCMAKE_EXE_LINKER_FLAGS="$FORCE_LOADS"

echo "== building FEBio Studio"
cmake --build "$BLD" -j"$NCPU"

APP="$BLD/bin/FEBioStudio.app"
test -d "$APP"
BIN="$APP/FEBioStudio"
test -f "$BIN"

# ------------------------------------------------------------- bundle
echo "== bundling model + launch storyboard"
cp "$ROOT/Model/tension-block.feb" "$APP/tension-block.feb"
if xcrun -f ibtool >/dev/null 2>&1; then
	xcrun ibtool --target-device ipad --minimum-deployment-target 17.0 \
		--compile "$APP/LaunchScreen.storyboardc" \
		"$ROOT/Studio/iOS/LaunchScreen.storyboard" \
		|| echo "WARNING: ibtool failed; app may run at scaled resolution"
else
	echo "WARNING: ibtool not found; app may run at scaled resolution"
fi
rm -rf "$APP/_CodeSignature"

# ------------------------------------------------------------- verify
echo "== verifying the app binary"
file "$BIN"
lipo -info "$BIN" | grep -q "arm64" || { echo "ERROR: binary is not arm64" >&2; exit 1; }
if strings "$BIN" | grep -q "QIOSIntegration"; then
	echo "   Qt iOS platform plugin: linked"
else
	echo "ERROR: QIOSIntegration plugin not found in binary — Qt platform plugin did not link" >&2
	exit 1
fi
if strings "$BIN" | grep -q "neo-Hookean"; then
	echo "   FEBio material registration: present"
else
	echo "WARNING: 'neo-Hookean' string not found — FEBio registration may be incomplete"
fi
/usr/libexec/PlistBuddy -c "Print :CFBundleIdentifier" "$APP/Info.plist"

# ------------------------------------------------------------ package
echo "== packaging IPA"
cd "$WORK"
rm -rf Payload FEBioStudio-unsigned.ipa
mkdir -p Payload
cp -R "$APP" Payload/
zip -qry "$ROOT/FEBioStudio-unsigned.ipa" Payload
ls -lh "$ROOT/FEBioStudio-unsigned.ipa"
echo "== done"
