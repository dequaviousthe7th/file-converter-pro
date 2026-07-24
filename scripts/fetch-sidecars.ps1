# fetch-sidecars.ps1 - download the sidecar binaries + pdfium library for a Windows build target.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\fetch-sidecars.ps1 x86_64-pc-windows-msvc
#
# Outputs (all gitignored):
#   src-tauri\binaries\ffmpeg-<triple>.exe
#   src-tauri\binaries\pandoc-<triple>.exe
#   src-tauri\binaries\typst-<triple>.exe
#   src-tauri\resources\pdfium\pdfium.dll
#
# Idempotent: any output that already exists with nonzero size is skipped.
# Only the needed binaries are extracted/kept (no ffprobe/ffplay).

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Target
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# VERSIONS - pinned. Keep in sync with scripts/fetch-sidecars.sh and
# licenses/README.md.
# ---------------------------------------------------------------------------
# ffmpeg: 8.1 release branch (8.1.x), GPL static build from BtbN FFmpeg-Builds
#         rolling "latest" tag (per-release checksums.sha256 verified below).
$FfmpegBranch   = 'n8.1'
$FfmpegBtbnBase = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest'
$PandocVersion  = '3.10.1'         # GPL-2.0-or-later - jgm/pandoc
$PandocBase     = "https://github.com/jgm/pandoc/releases/download/$PandocVersion"
$TypstVersion   = '0.15.1'         # Apache-2.0 - typst/typst
$TypstBase      = "https://github.com/typst/typst/releases/download/v$TypstVersion"
$PdfiumRelease  = 'chromium/7961'  # Apache-2.0 & BSD-3-Clause - bblanchon non-V8 build
$PdfiumBase     = 'https://github.com/bblanchon/pdfium-binaries/releases/download/chromium%2F7961'
# ---------------------------------------------------------------------------

if ($Target -ne 'x86_64-pc-windows-msvc') {
    throw "fetch-sidecars.ps1 supports only x86_64-pc-windows-msvc (got '$Target'). Use scripts/fetch-sidecars.sh for macOS/Linux targets."
}

$Root      = Split-Path -Parent $PSScriptRoot
$BinDir    = Join-Path $Root 'src-tauri\binaries'
$PdfiumDir = Join-Path $Root 'src-tauri\resources\pdfium'
$Tmp       = Join-Path ([System.IO.Path]::GetTempPath()) ('fetch-sidecars-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $BinDir, $PdfiumDir, $Tmp | Out-Null

function Get-RemoteFile {
    param([string]$Url, [string]$Dest)
    & curl.exe -L --retry 3 --retry-delay 2 --fail --silent --show-error -o $Dest $Url
    if ($LASTEXITCODE -ne 0) { throw "download failed: $Url" }
}

function Test-Sha256 {
    # Verify against a published checksums file (BtbN only - pandoc/typst/pdfium
    # do not publish per-asset sha256 files).
    param([string]$Archive, [string]$ChecksumsUrl)
    if (-not $ChecksumsUrl) { return }
    $sums = Join-Path $Tmp 'checksums.sha256'
    if (-not (Test-Path $sums)) { Get-RemoteFile $ChecksumsUrl $sums }
    $name = Split-Path -Leaf $Archive
    $line = Get-Content $sums | Where-Object { ($_ -split '\s+')[-1].TrimStart('*') -eq $name } | Select-Object -First 1
    if (-not $line) {
        Write-Host "       (no published checksum for $name - skipping verification)"
        return
    }
    $expected = ($line -split '\s+')[0]
    $actual   = (Get-FileHash -Algorithm SHA256 -Path $Archive).Hash
    if ($actual -ne $expected) {   # PowerShell string comparison is case-insensitive
        throw "sha256 mismatch for ${name}: expected $expected, got $actual"
    }
    Write-Host '       sha256 OK'
}

function Invoke-FetchComponent {
    param(
        [string]$Label,
        [string]$Url,
        [string]$Pattern,      # tar glob for selective extraction
        [string]$BinName,
        [string]$Dest,
        [string]$ChecksumsUrl = ''
    )
    if ((Test-Path $Dest) -and ((Get-Item $Dest).Length -gt 0)) {
        Write-Host "skip   $Label - $(Split-Path -Leaf $Dest) already present"
        return
    }
    Write-Host "fetch  $Label"
    Write-Host "       $Url"
    $work = Join-Path $Tmp $Label
    New-Item -ItemType Directory -Force -Path $work | Out-Null
    $archive = Join-Path $work ([System.IO.Path]::GetFileName(([uri]$Url).LocalPath))
    Get-RemoteFile $Url $archive
    Test-Sha256 $archive $ChecksumsUrl

    $unpacked = Join-Path $work 'unpacked'
    New-Item -ItemType Directory -Force -Path $unpacked | Out-Null
    # bsdtar (tar.exe, present on windows-latest) reads both .zip and .tgz and
    # supports member globs, so extract only what we need; fall back to a full
    # Expand-Archive for zips if the pattern misses.
    & tar.exe -xf $archive -C $unpacked "*$Pattern" 2>$null
    if ($LASTEXITCODE -ne 0) {
        if ($archive -like '*.zip') {
            Expand-Archive -Path $archive -DestinationPath $unpacked -Force
        }
        else {
            & tar.exe -xf $archive -C $unpacked
            if ($LASTEXITCODE -ne 0) { throw "extraction failed: $archive" }
        }
    }

    $src = Get-ChildItem -Path $unpacked -Recurse -File -Filter $BinName | Select-Object -First 1
    if (-not $src) { throw "'$BinName' not found inside $(Split-Path -Leaf $archive)" }
    Copy-Item $src.FullName $Dest -Force
    Remove-Item -Recurse -Force $work   # free disk before the next large archive
    Write-Host "ok     $Dest"
}

Write-Host "Fetching sidecars for $Target"
Write-Host "  ffmpeg $($FfmpegBranch.TrimStart('n')).x (GPL) | pandoc $PandocVersion | typst $TypstVersion | pdfium $PdfiumRelease"
Write-Host ''

$ffmpegZip = "ffmpeg-$FfmpegBranch-latest-win64-gpl-$($FfmpegBranch.TrimStart('n')).zip"
Invoke-FetchComponent -Label 'ffmpeg' -Url "$FfmpegBtbnBase/$ffmpegZip" `
    -Pattern 'bin/ffmpeg.exe' -BinName 'ffmpeg.exe' `
    -Dest (Join-Path $BinDir "ffmpeg-$Target.exe") `
    -ChecksumsUrl "$FfmpegBtbnBase/checksums.sha256"

Invoke-FetchComponent -Label 'pandoc' -Url "$PandocBase/pandoc-$PandocVersion-windows-x86_64.zip" `
    -Pattern 'pandoc.exe' -BinName 'pandoc.exe' `
    -Dest (Join-Path $BinDir "pandoc-$Target.exe")

Invoke-FetchComponent -Label 'typst' -Url "$TypstBase/typst-x86_64-pc-windows-msvc.zip" `
    -Pattern 'typst.exe' -BinName 'typst.exe' `
    -Dest (Join-Path $BinDir "typst-$Target.exe")

Invoke-FetchComponent -Label 'pdfium' -Url "$PdfiumBase/pdfium-win-x64.tgz" `
    -Pattern 'pdfium.dll' -BinName 'pdfium.dll' `
    -Dest (Join-Path $PdfiumDir 'pdfium.dll')

Remove-Item -Recurse -Force $Tmp -ErrorAction SilentlyContinue

Write-Host ''
Write-Host "== Sidecars for $Target =="
foreach ($f in @(
        (Join-Path $BinDir "ffmpeg-$Target.exe"),
        (Join-Path $BinDir "pandoc-$Target.exe"),
        (Join-Path $BinDir "typst-$Target.exe"),
        (Join-Path $PdfiumDir 'pdfium.dll')
    )) {
    $item = Get-Item $f
    Write-Host ('{0,10:N1} MB  {1}' -f ($item.Length / 1MB), $item.FullName)
}
