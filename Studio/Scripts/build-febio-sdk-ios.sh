#!/bin/bash
# Cross-compile the FEBio SDK (v4.13 release) for iOS arm64, for use
# by the FEBio Studio port. Adapted from the spike's
# Scripts/build-febio-ios.sh with two deliberate differences:
#
#   * FEBio is pinned to the v4.13 RELEASE TAG, not the spike's
#     develop snapshot. Reason (found by run 40772868459): Studio
#     3.2.0's FSCore/Archive.h calls vec2d::x()/y() accessors that
#     FEBio develop REMOVED in commit 15edba277c (2026-05-19,
#     "Modified vec2d class to be more consistent with other vector
#     classes"). The v4.13 release tag predates that change and
#     still has the accessors — it is the SDK Studio 3.2.0 pairs
#     with. The spike keeps its own (device-verified) pin.
#   * Output goes to build/studio/febio/ so the spike's build tree
#     is never touched.
#
# The two build-system patches in Patches/ (repo root) are reused
# unchanged — verified to apply cleanly to this tag.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FEBIO_COMMIT="32ae206ff4881dfb54f62296cd1558e58ed9fcc6"
WORK="$ROOT/build/studio/febio"
SRC="$WORK/src"
# The v4.13 tag's FEBioConfig.cmake (older than develop's) has no
# FEBio_BUILD_DIR support: its in-tree mode looks for the libraries
# under <source>/build/lib. So the build tree lives INSIDE the
# source tree, exactly where that config expects it.
BLD="$SRC/build"

mkdir -p "$WORK"

if [ ! -f "$WORK/.febio-src.stamp" ]; then
	echo "== fetching FEBio v4.13 @ $FEBIO_COMMIT (codeload archive)"
	rm -rf "$SRC" "$WORK/FEBio-$FEBIO_COMMIT" "$WORK/febio.tar.gz"
	curl -sfL -o "$WORK/febio.tar.gz" "https://codeload.github.com/febiosoftware/FEBio/tar.gz/$FEBIO_COMMIT"
	tar -xzf "$WORK/febio.tar.gz" -C "$WORK"
	mkdir -p "$SRC"
	cp -R "$WORK/FEBio-$FEBIO_COMMIT/." "$SRC/"
	rm -rf "$WORK/FEBio-$FEBIO_COMMIT" "$WORK/febio.tar.gz"
	git -C "$SRC" init -q  # so `git apply` behaves for Patches/
	touch "$WORK/.febio-src.stamp"
fi

echo "== applying patches"
for p in "$ROOT"/Patches/*.patch; do
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

echo "== configuring FEBio SDK (v4.13) for iOS arm64"
cmake -S "$SRC" -B "$BLD" \
	-DCMAKE_TOOLCHAIN_FILE="$ROOT/Scripts/ios.toolchain.cmake" \
	-DCMAKE_OSX_SYSROOT=iphoneos \
	-DCMAKE_BUILD_TYPE=Release \
	-DFEBIO_LIB_TYPE=STATIC \
	-DSET_DEVCOMMIT=OFF

echo "== building FEBio SDK libraries"
cmake --build "$BLD" -j"$(sysctl -n hw.ncpu)" --target \
	fecore numcore febioxml feimglib febioplot \
	febiomech febiomix febiofluid febioopt feamr febiorve febiolib \
	febcode febiotest

mkdir -p "$WORK/lib"
cp "$BLD"/lib/*.a "$WORK/lib/"
echo "== iOS FEBio SDK libraries:"
ls -lh "$WORK/lib"
