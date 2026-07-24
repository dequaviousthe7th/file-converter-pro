# Releasing File Converter Pro

Runbook for cutting a release. CI does the heavy lifting; your job is four
version bumps, one tag, one approval click, and one Publish button.

## 0. Prerequisites (one-time)

- Push access to `dequaviousthe7th/file-converter`.
- Signing credentials configured (all optional — builds succeed unsigned without
  them; see the table at the bottom and `docs/SIGNING.md`).
- For Windows signing: the SignPath project `file-converter-pro` with signing
  policy `release-signing`, and access to the SignPath web UI to approve requests.

## 1. Bump the version (three files, keep them identical)

| File | Field |
|---|---|
| `src-tauri/tauri.conf.json` | `version` |
| `Cargo.toml` (repo root) | `[workspace.package] version` |
| `package.json` | `version` |

Also add a `CHANGELOG.md` entry for the new version.

Sanity check before committing:

```bash
grep '"version"' src-tauri/tauri.conf.json package.json
grep -A2 '\[workspace.package\]' Cargo.toml
```

All three must show the same `X.Y.Z`.

## 2. Commit, tag, push

```bash
git add -A && git commit -m "release: vX.Y.Z"
git push origin main
git tag vX.Y.Z
git push origin vX.Y.Z
```

The tag push triggers `.github/workflows/release.yml`. (You can also run the
workflow manually via **Actions → Release → Run workflow** for a dry run — it
builds from the selected branch and creates/updates the same draft release.)

## 3. What CI does

Four matrix jobs run in parallel:

| Runner | Target | Artifacts |
|---|---|---|
| windows-latest | x86_64-pc-windows-msvc | NSIS `*-setup.exe` |
| macos-latest | aarch64-apple-darwin | `.dmg` (Apple Silicon) |
| macos-latest | x86_64-apple-darwin | `.dmg` (Intel) |
| ubuntu-22.04 | x86_64-unknown-linux-gnu | `.AppImage`, `.deb`, `SHA256SUMS` (+ `.asc` if GPG key configured) |

Each job: `npm ci` → rust toolchain for the target → `scripts/fetch-sidecars`
(downloads pinned ffmpeg/pandoc/typst/pdfium for that triple) →
`tauri-apps/tauri-action` builds and uploads bundles to a **draft** GitHub
Release named `File Converter Pro vX.Y.Z` (tag `vX.Y.Z`).

Signing happens automatically per platform when credentials exist:

- **macOS** — if the `APPLE_*` secrets are set, Tauri signs with your
  Developer ID and notarizes during the build. No action needed from you.
- **Windows** — if the repo variable `SIGNPATH_ORGANIZATION_ID` is set, the
  job uploads the unsigned installer to SignPath and **waits for your
  approval** (see step 4). The signed installer then replaces the unsigned
  asset on the draft release.
- **Linux** — `SHA256SUMS` is always generated and attached; it is GPG-signed
  (`SHA256SUMS.asc`) when `GPG_PRIVATE_KEY` is set.
- **Updater** — `TAURI_SIGNING_PRIVATE_KEY` / `_PASSWORD` are passed through
  when present (only relevant once updater artifacts are enabled).

Missing credentials never fail the build — the affected artifact just ships
unsigned.

## 4. Approve the SignPath request (Windows signing only)

While the Windows job is running you will get a SignPath notification (and the
job log shows "waiting for completion"):

1. Open the SignPath web UI (app.signpath.io) → organization → project
   `file-converter-pro` → **Signing requests**.
2. Verify the request originates from this repo's Release workflow for the
   expected tag/commit (SignPath's origin verification shows this).
3. Click **Approve**.

The workflow waits up to **2 hours** for the approval. If it times out or you
deny by mistake, re-run just the failed Windows job from the Actions UI — the
draft release and other platforms' assets are unaffected.

## 5. Verify and publish the draft

1. GitHub → Releases → the draft `File Converter Pro vX.Y.Z`.
2. Check all expected assets are present: 1 `.exe`, 2 `.dmg`, `.AppImage`,
   `.deb`, `SHA256SUMS` (+ `.asc`).
3. Spot-check: download the Windows installer and confirm the digital
   signature (Properties → Digital Signatures → "SignPath Foundation") if
   Windows signing is enabled; `sha256sum -c SHA256SUMS` against the Linux
   downloads.
4. Write the release notes (the draft body), then click **Publish release**.

Nothing is public until you publish.

## 6. First-release expectations (SmartScreen etc.)

- **Signed via SignPath Foundation:** the publisher shown is "SignPath
  Foundation", which carries shared SmartScreen reputation — the classic
  "Windows protected your PC" wall is effectively gone from release one.
  However, **per-file-hash reputation still exists**: the very first downloads
  of any brand-new installer can occasionally show a milder browser warning in
  Chrome/Edge ("not commonly downloaded"). This fades within the first
  days/hundreds of downloads. Don't panic; don't re-upload the file (that
  resets the hash).
- **Unsigned Windows builds** (before SignPath enrollment completes): expect
  the full SmartScreen interstitial ("Windows protected your PC → More info →
  Run anyway") and possible Defender heuristics on the NSIS installer. This is
  normal for unsigned NSIS; enrolling in SignPath is the fix, not re-building.
- **macOS:** unsigned/un-notarized builds are effectively unusable for
  non-technical users on macOS 15+ (no right-click-open bypass anymore). Do
  not advertise the macOS downloads until the `APPLE_*` secrets are in place.
- Mitigations that help reputation accrue: keep the same publisher identity
  forever, never strip timestamps, and submit any Defender false positive to
  Microsoft Security Intelligence (signed submissions are fast-tracked).

## Secrets and variables the release workflow reads

| Name | Kind | Purpose |
|---|---|---|
| `APPLE_CERTIFICATE` | secret | base64 `.p12` Developer ID Application cert |
| `APPLE_CERTIFICATE_PASSWORD` | secret | password for the `.p12` |
| `APPLE_SIGNING_IDENTITY` | secret | e.g. `Developer ID Application: Name (TEAMID)` |
| `APPLE_ID` / `APPLE_PASSWORD` / `APPLE_TEAM_ID` | secret | notarization via Apple ID + app-specific password |
| `APPLE_API_KEY` / `APPLE_API_ISSUER` | secret | notarization via App Store Connect API key (preferred; use instead of the three above) |
| `APPLE_API_KEY_PATH` **or** `APPLE_API_KEY_CONTENT` | secret | path to the `.p8`, or its raw content (CI writes it to a temp file) |
| `SIGNPATH_ORGANIZATION_ID` | **variable** | enables the whole SignPath flow when non-empty |
| `SIGNPATH_API_TOKEN` | secret | SignPath CI user API token |
| `GPG_PRIVATE_KEY` / `GPG_PASSPHRASE` | secret | armored private key (+ optional passphrase) for signing `SHA256SUMS` |
| `TAURI_SIGNING_PRIVATE_KEY` / `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | secret | Tauri updater minisign key (future use) |

Every one of these is optional; absent values simply skip the corresponding
signing step. Enrollment walk-throughs live in `docs/SIGNING.md`.
