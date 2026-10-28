#!/bin/bash
# Cross-compile the FEBio solver core for iOS arm64 (static libs).
#
# Clones FEBio from its official GitHub at the pinned commit, applies
# the patches in Patches/ (each one enumerated there), and builds the
# module libraries with MKL OFF (bundled Skyline solver fallback).
# Output: build/febio/lib/lib*.a plus the source tree at
# build/febio/src (the app target's header search path).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FEBIO_COMMIT="9605327359ded64ea0d65dd1aeca484fc45a9acd"
WORK="$ROOT/build/febio"
SRC="$WORK/src"
BLD="$WORK/build"

mkdir -p "$WORK"

if [ ! -f "$WORK/.febio-src.stamp" ]; then
	echo "== fetching FEBio @ $FEBIO_COMMIT (codeload archive)"
	# NOTE: a plain `git fetch` of a pinned SHA fails on the CI runner
	# (git demands credentials non-interactively). The codeload zip of
	# the commit needs no auth and is byte-identical source.
	rm -rf "$SRC" "$WORK/FEBio-$FEBIO_COMMIT" "$WORK/febio.zip"
	curl -sfL -o "$WORK/febio.zip" "https://codeload.github.com/febiosoftware/FEBio/zip/$FEBIO_COMMIT"
	unzip -q "$WORK/febio.zip" -d "$WORK"
	mkdir -p "$SRC"
	cp -R "$WORK/FEBio-$FEBIO_COMMIT/." "$SRC/"
	rm -rf "$WORK/FEBio-$FEBIO_COMMIT" "$WORK/febio.zip"
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

echo "== configuring FEBio for iOS arm64"
cmake -S "$SRC" -B "$BLD" \
	-DCMAKE_TOOLCHAIN_FILE="$ROOT/Scripts/ios.toolchain.cmake" \
	-DCMAKE_OSX_SYSROOT=iphoneos \
	-DCMAKE_BUILD_TYPE=Release \
	-DFEBIO_LIB_TYPE=STATIC \
	-DSET_DEVCOMMIT=OFF

echo "== building FEBio libraries"
cmake --build "$BLD" -j"$(sysctl -n hw.ncpu)" --target \
	fecore numcore febioxml feimglib febioplot \
	febiomech febiomix febiofluid febioopt feamr febiorve febiolib

mkdir -p "$WORK/lib"
cp "$BLD"/lib/*.a "$WORK/lib/"
echo "== iOS FEBio libraries:"
ls -lh "$WORK/lib"
