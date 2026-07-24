#!/usr/bin/env bash
#
# fetch-sidecars.sh — download the sidecar binaries + pdfium library for one build target.
#
# Usage:
#   bash scripts/fetch-sidecars.sh <rust-target-triple>
#
# Supported triples:
#   x86_64-pc-windows-msvc      (Windows CI normally uses scripts/fetch-sidecars.ps1)
#   aarch64-apple-darwin
#   x86_64-apple-darwin
#   x86_64-unknown-linux-gnu
#
# Outputs (all gitignored):
#   src-tauri/binaries/ffmpeg-<triple>[.exe]
#   src-tauri/binaries/pandoc-<triple>[.exe]
#   src-tauri/binaries/typst-<triple>[.exe]
#   src-tauri/resources/pdfium/{pdfium.dll | libpdfium.dylib | libpdfium.so}
#
# Idempotent: any output that already exists with nonzero size is skipped.
# Only the needed binaries are extracted/kept (no ffprobe/ffplay).

set -euo pipefail

# ---------------------------------------------------------------------------
# VERSIONS — pinned. Update deliberately and keep licenses/README.md in sync.
# ---------------------------------------------------------------------------
# ffmpeg: 8.1 release branch (8.1.x), GPL static builds.
#   - Windows/Linux: BtbN FFmpeg-Builds rolling "latest" tag, n8.1 branch assets
#     (per-release checksums.sha256 is published and verified below).
#   - macOS: ffmpeg.martin-riedl.de latest *release* channel build (8.1.x,
#     signed binaries; re-signed under our own identity at bundling time).
FFMPEG_BRANCH="n8.1"
FFMPEG_BTBN_BASE="https://github.com/BtbN/FFmpeg-Builds/releases/download/latest"
FFMPEG_MACOS_BASE="https://ffmpeg.martin-riedl.de/redirect/latest/macos"
PANDOC_VERSION="3.10.1"        # GPL-2.0-or-later — jgm/pandoc
PANDOC_BASE="https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}"
TYPST_VERSION="0.15.1"         # Apache-2.0 — typst/typst
TYPST_BASE="https://github.com/typst/typst/releases/download/v${TYPST_VERSION}"
PDFIUM_RELEASE="chromium/7961" # Apache-2.0 & BSD-3-Clause — bblanchon non-V8 build
PDFIUM_BASE="https://github.com/bblanchon/pdfium-binaries/releases/download/chromium%2F7961"
# ---------------------------------------------------------------------------

usage() {
  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
}

TRIPLE="${1:-}"
[[ -n "$TRIPLE" ]] || usage

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="$ROOT/src-tauri/binaries"
PDFIUM_DIR="$ROOT/src-tauri/resources/pdfium"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

EXE=""
case "$TRIPLE" in
  x86_64-pc-windows-msvc)
    EXE=".exe"
    FFMPEG_URL="$FFMPEG_BTBN_BASE/ffmpeg-${FFMPEG_BRANCH}-latest-win64-gpl-${FFMPEG_BRANCH#n}.zip"
    FFMPEG_SHA_URL="$FFMPEG_BTBN_BASE/checksums.sha256"
    FFMPEG_PATTERN="bin/ffmpeg.exe"
    PANDOC_URL="$PANDOC_BASE/pandoc-${PANDOC_VERSION}-windows-x86_64.zip"
    PANDOC_PATTERN="pandoc.exe"
    TYPST_URL="$TYPST_BASE/typst-x86_64-pc-windows-msvc.zip"
    TYPST_PATTERN="typst.exe"
    PDFIUM_URL="$PDFIUM_BASE/pdfium-win-x64.tgz"
    PDFIUM_LIB="pdfium.dll"
    ;;
  aarch64-apple-darwin)
    FFMPEG_URL="$FFMPEG_MACOS_BASE/arm64/release/ffmpeg.zip"
    FFMPEG_SHA_URL=""
    FFMPEG_PATTERN="ffmpeg"
    PANDOC_URL="$PANDOC_BASE/pandoc-${PANDOC_VERSION}-arm64-macOS.zip"
    PANDOC_PATTERN="bin/pandoc"
    TYPST_URL="$TYPST_BASE/typst-aarch64-apple-darwin.tar.xz"
    TYPST_PATTERN="typst"
    PDFIUM_URL="$PDFIUM_BASE/pdfium-mac-arm64.tgz"
    PDFIUM_LIB="libpdfium.dylib"
    ;;
  x86_64-apple-darwin)
    FFMPEG_URL="$FFMPEG_MACOS_BASE/amd64/release/ffmpeg.zip"
    FFMPEG_SHA_URL=""
    FFMPEG_PATTERN="ffmpeg"
    PANDOC_URL="$PANDOC_BASE/pandoc-${PANDOC_VERSION}-x86_64-macOS.zip"
    PANDOC_PATTERN="bin/pandoc"
    TYPST_URL="$TYPST_BASE/typst-x86_64-apple-darwin.tar.xz"
    TYPST_PATTERN="typst"
    PDFIUM_URL="$PDFIUM_BASE/pdfium-mac-x64.tgz"
    PDFIUM_LIB="libpdfium.dylib"
    ;;
  x86_64-unknown-linux-gnu)
    FFMPEG_URL="$FFMPEG_BTBN_BASE/ffmpeg-${FFMPEG_BRANCH}-latest-linux64-gpl-${FFMPEG_BRANCH#n}.tar.xz"
    FFMPEG_SHA_URL="$FFMPEG_BTBN_BASE/checksums.sha256"
    FFMPEG_PATTERN="bin/ffmpeg"
    PANDOC_URL="$PANDOC_BASE/pandoc-${PANDOC_VERSION}-linux-amd64.tar.gz"
    PANDOC_PATTERN="bin/pandoc"
    TYPST_URL="$TYPST_BASE/typst-x86_64-unknown-linux-musl.tar.xz"
    TYPST_PATTERN="typst"
    PDFIUM_URL="$PDFIUM_BASE/pdfium-linux-x64.tgz"
    PDFIUM_LIB="libpdfium.so"
    ;;
  *)
    echo "ERROR: unsupported target triple '$TRIPLE'" >&2
    usage
    ;;
esac

download() { # <url> <dest>
  curl -L --retry 3 --retry-delay 2 --fail --silent --show-error -o "$2" "$1"
}

# Verify a downloaded archive against a published checksums file (BtbN only —
# pandoc/typst/pdfium/martin-riedl do not publish per-asset sha256 files).
verify_sha256() { # <archive> <checksums-url>
  local archive="$1" sha_url="$2"
  [[ -n "$sha_url" ]] || return 0
  if ! command -v sha256sum >/dev/null 2>&1; then
    echo "       (sha256sum not available — skipping checksum verification)"
    return 0
  fi
  local sums="$TMP/checksums.sha256"
  [[ -s "$sums" ]] || download "$sha_url" "$sums"
  local name expected actual
  name="$(basename "$archive")"
  expected="$(awk -v n="$name" '$NF == n || $NF == "*"n {print $1; exit}' "$sums")"
  if [[ -z "$expected" ]]; then
    echo "       (no published checksum for $name — skipping verification)"
    return 0
  fi
  actual="$(sha256sum "$archive" | awk '{print $1}')"
  if [[ "$actual" != "$expected" ]]; then
    echo "ERROR: sha256 mismatch for $name" >&2
    echo "  expected: $expected" >&2
    echo "  actual:   $actual" >&2
    return 1
  fi
  echo "       sha256 OK"
}

# Extract only the members matching <pattern> when the tool allows it;
# fall back to a full extraction (the copy step still takes just one file).
extract() { # <archive> <outdir> <pattern>
  local archive="$1" outdir="$2" pattern="$3"
  mkdir -p "$outdir"
  case "$archive" in
    *.zip)
      if command -v unzip >/dev/null 2>&1; then
        unzip -q -o "$archive" "*${pattern}" -d "$outdir" 2>/dev/null \
          || unzip -q -o "$archive" -d "$outdir"
      else
        tar -xf "$archive" -C "$outdir" # bsdtar reads zip
      fi
      ;;
    *)
      if tar --version 2>/dev/null | grep -qi 'gnu tar'; then
        tar -xf "$archive" -C "$outdir" --wildcards --no-anchored "$pattern" 2>/dev/null \
          || tar -xf "$archive" -C "$outdir"
      else
        tar -xf "$archive" -C "$outdir" "*${pattern}" 2>/dev/null \
          || tar -xf "$archive" -C "$outdir"
      fi
      ;;
  esac
}

fetch_component() { # <label> <url> <pattern> <binname> <dest> [checksums-url]
  local label="$1" url="$2" pattern="$3" binname="$4" dest="$5" sha_url="${6:-}"
  if [[ -s "$dest" ]]; then
    echo "skip   $label — $(basename "$dest") already present"
    return 0
  fi
  echo "fetch  $label"
  echo "       $url"
  local work="$TMP/$label"
  mkdir -p "$work"
  local archive="$work/$(basename "$url")"
  download "$url" "$archive"
  verify_sha256 "$archive" "$sha_url"
  extract "$archive" "$work/unpacked" "$pattern"
  local src
  src="$(find "$work/unpacked" -type f -name "$binname" 2>/dev/null | head -n 1)"
  if [[ -z "$src" ]]; then
    echo "ERROR: '$binname' not found inside $(basename "$url")" >&2
    return 1
  fi
  mkdir -p "$(dirname "$dest")"
  cp "$src" "$dest"
  chmod +x "$dest"
  rm -rf "$work" # free disk before the next large archive
  echo "ok     $dest"
}

echo "Fetching sidecars for $TRIPLE"
echo "  ffmpeg ${FFMPEG_BRANCH#n}.x (GPL) | pandoc $PANDOC_VERSION | typst $TYPST_VERSION | pdfium $PDFIUM_RELEASE"
echo

fetch_component ffmpeg "$FFMPEG_URL" "$FFMPEG_PATTERN" "ffmpeg$EXE" \
  "$BIN_DIR/ffmpeg-$TRIPLE$EXE" "$FFMPEG_SHA_URL"
fetch_component pandoc "$PANDOC_URL" "$PANDOC_PATTERN" "pandoc$EXE" \
  "$BIN_DIR/pandoc-$TRIPLE$EXE"
fetch_component typst "$TYPST_URL" "$TYPST_PATTERN" "typst$EXE" \
  "$BIN_DIR/typst-$TRIPLE$EXE"
fetch_component pdfium "$PDFIUM_URL" "$PDFIUM_LIB" "$PDFIUM_LIB" \
  "$PDFIUM_DIR/$PDFIUM_LIB"

echo
echo "== Sidecars for $TRIPLE =="
for f in \
  "$BIN_DIR/ffmpeg-$TRIPLE$EXE" \
  "$BIN_DIR/pandoc-$TRIPLE$EXE" \
  "$BIN_DIR/typst-$TRIPLE$EXE" \
  "$PDFIUM_DIR/$PDFIUM_LIB"; do
  printf '%8s  %s\n' "$(du -h "$f" | cut -f1)" "$f"
done
