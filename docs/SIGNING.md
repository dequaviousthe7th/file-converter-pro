# Code Signing Setup

This guide walks through enrolling in the signing programs used by the release pipeline
(`.github/workflows/release.yml`). The workflows are built so that **unsigned builds still
work** — every signing step is conditional on its secrets/variables being present, so the
app ships first and signing activates the moment enrollment completes.

State of the world this guide is based on: researched July 2026.

---

## 1. Why the plan looks like this (2026 reality)

- **EV certificates lost their SmartScreen advantage in August 2024.** Microsoft removed all
  EV code-signing OIDs from the Trusted Root Program; EV and OV certs are now treated
  identically by SmartScreen. Reputation accrues per **publisher identity + file hash**
  through clean-download volume, regardless of cert type. Paying $300+/yr for EV to skip
  SmartScreen is pointless.
  ([ToDesktop PSA](https://www.todesktop.com/blog/posts/windows-apps-psa-ev-certs-do-not-grant-immediate-reputation-anymore),
  [Microsoft SmartScreen docs](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation))
- **There is no product that guarantees zero warnings on the very first downloads of a
  brand-new publisher.** SmartScreen clears when either the file hash has enough
  clean-download history or the signing publisher identity has accumulated reputation.
- **macOS is non-negotiable.** macOS Sequoia removed the Control-click → Open bypass (and
  Tahoe keeps it removed); unsigned apps require a buried System Settings override that
  non-technical users will not find. Apple Developer Program + notarization is required.
  ([Apple dev note](https://developer.apple.com/news/?id=saqachfa))

**Chosen plan:** SignPath Foundation (Windows, free) + Apple Developer Program (macOS,
$99/yr) + GPG-signed checksums (Linux, free). Total: **$99/year**.

---

## 2. Windows — SignPath Foundation (primary, free)

[SignPath Foundation](https://signpath.io/solutions/open-source-community) provides free
managed code signing for qualifying open-source projects: a free SignPath.io subscription
plus signing under a certificate issued to **"SignPath Foundation"**. Because that publisher
identity signs many established OSS projects, it carries shared, pre-existing SmartScreen
reputation — in practice, signed releases don't trigger SmartScreen from release one.

Trade-off: the displayed publisher is "SignPath Foundation", not your own name.

### Eligibility checklist (all must be true)

- [ ] OSI-approved license (this repo is MIT ✓)
- [ ] No commercial dual-licensing
- [ ] No proprietary components
- [ ] Actively maintained
- [ ] Already has published releases
- [ ] Functionality documented on the download page
- [ ] A **code signing policy** published on the project homepage
      (this repo: [`.github/signing-policy.md`](../.github/signing-policy.md))
- [ ] Team roles defined (author / reviewer / approver — can all be you for a solo project)
- [ ] MFA enabled on GitHub **and** on your SignPath account
- [ ] Releases are **automated CI builds traceable to the repository source**
      (origin verification is enforced — our `release.yml` satisfies this)

Full terms: [signpath.org/terms.html](https://signpath.org/terms.html)

### Application steps

1. Enable MFA on your GitHub account if you haven't already.
2. Make sure the signing policy page and at least one published release exist.
3. Apply via the [SignPath open-source program page](https://signpath.io/solutions/open-source-community)
   — you'll provide the project name, repository URL, license, download page, a short
   description, and your team roles.
4. **Expected wait: days to weeks** for the application review.
5. On approval you get a SignPath organization with a project and a `release-signing`
   signing policy. Configure the artifact as a `pe-file`.
6. Create an API token in the SignPath UI, then in this GitHub repo add:
   - **Secret** `SIGNPATH_API_TOKEN` — the API token
   - **Variable** `SIGNPATH_ORGANIZATION_ID` — your SignPath organization ID
     (the presence of this variable is what activates the Windows signing steps in
     `release.yml`)
7. **Every release requires a manual approval click** in the SignPath UI — the workflow
   submits the signing request and waits; you approve it, the signed installer replaces the
   unsigned release asset.

References: [SignPath GitHub Action](https://github.com/SignPath/github-action-submit-signing-request),
[artifact configuration reference](https://docs.signpath.io/artifact-configuration/reference)

---

## 3. macOS — Apple Developer ID + notarization ($99/yr)

### Enroll

1. Enroll in the [Apple Developer Program](https://developer.apple.com/programs/enroll/)
   ($99 USD/year; individuals are fine, no company needed). Requires an Apple ID with
   two-factor authentication.

### Create the Developer ID Application certificate

2. On a Mac: **Keychain Access → Certificate Assistant → Request a Certificate From a
   Certificate Authority** → save the CSR to disk.
3. At [developer.apple.com](https://developer.apple.com/account/resources/certificates/list):
   **Certificates → + → Developer ID Application** → upload the CSR → download the
   certificate → double-click to import it into your Keychain.
4. In Keychain Access, expand the certificate, select **both** the certificate and its
   private key, right-click → **Export** → save as a `.p12` with a strong password.
5. Base64-encode it for GitHub: `base64 -i certificate.p12 | pbcopy`

### Create an App Store Connect API key (for notarization — preferred for CI)

6. In [App Store Connect](https://appstoreconnect.apple.com): **Users and Access →
   Integrations → App Store Connect API → Team Keys → +** (Developer role is sufficient).
7. Download the `.p8` key file (you can only download it once) and note the **Key ID** and
   **Issuer ID**.

### Add the GitHub secrets

| Secret | Value |
|--------|-------|
| `APPLE_CERTIFICATE` | base64 of the Developer ID Application `.p12` |
| `APPLE_CERTIFICATE_PASSWORD` | the `.p12` export password |
| `APPLE_SIGNING_IDENTITY` | `Developer ID Application: Your Name (TEAMID)` |
| `APPLE_API_KEY` | App Store Connect API **Key ID** |
| `APPLE_API_ISSUER` | App Store Connect **Issuer ID** (UUID) |
| `APPLE_API_KEY_PATH` | path to the `.p8` key file on the runner |

Alternative to the API key (Apple-ID-based notarization): `APPLE_ID` +
`APPLE_PASSWORD` (an [app-specific password](https://support.apple.com/en-us/102654)) +
`APPLE_TEAM_ID`. The App Store Connect API key is preferred for CI.

Once `APPLE_CERTIFICATE` is present, `release.yml` signs and notarizes the macOS builds
automatically via the Tauri bundler. Notarization itself is free and takes minutes.

References: [Tauri macOS signing docs](https://v2.tauri.app/distribute/sign/macos/),
[Tauri environment-variable reference](https://v2.tauri.app/reference/environment-variables/)

---

## 4. Linux — GPG-signed checksums (free)

No OS gatekeeper blocks unsigned Linux binaries. The convention users and packagers
actually check is a GPG-signed checksums file:

1. Generate or reuse a GPG key: `gpg --full-generate-key`
2. Export the private key and add it as the GitHub secret `GPG_PRIVATE_KEY`.
3. Publish your public key (in the repo or on a keyserver) so users can verify.

When the secret is present, `release.yml` signs the `SHA256SUMS` file attached to each
release.

Reference: [Tauri Linux signing docs](https://v2.tauri.app/distribute/sign/linux/)

---

## 5. Fallbacks if SignPath doesn't work out

### Certum Open Source Code Signing (~$50–58/yr, works for any individual worldwide)

- Cloud (SimplySign) open-source code signing cert; subject reads
  `Open Source Developer, <Your Name>` — individual ID verification, no company, no
  geographic restriction.
  ([Certum shop](https://shop.certum.eu/open-source-code-signing-on-simplysign.html),
  [certum.store listing](https://certum.store/open-source-code-signing-on-simplysign.html),
  [experience report](https://piers.rocks/2025/10/30/certum-open-source-code-sign.html))
- Choose the **SimplySign cloud** variant (virtual smartcard), not the physical card/reader.
- Downsides: standard reputation ramp — first releases **will** show SmartScreen until
  downloads accumulate; CI automation is clunky (SimplySign Desktop is interactive), so
  expect to sign locally or on a self-hosted runner.

### Azure Artifact Signing ($9.99/mo, US/CA individuals only)

- Formerly "Azure Trusted Signing"; GA since January 2026. Basic tier is
  **$9.99/account/month** (5,000 signatures/mo).
  ([product page](https://azure.microsoft.com/en-us/products/artifact-signing),
  [pricing](https://azure.microsoft.com/en-us/pricing/details/artifact-signing/),
  [FAQ](https://learn.microsoft.com/en-us/azure/artifact-signing/faq))
- **Eligibility as of July 2026: individuals in the USA and Canada only** (organizations:
  US/CA/EU/UK+). If you're an individual outside those regions, this is off the table until
  Microsoft expands coverage — re-check every few months.
- Identity validation via government ID through Microsoft Entra Verified ID; your validated
  legal name becomes the cert subject; short-lived certs, keys in Microsoft-managed HSM.
- Integrates with Tauri via `bundle.windows.signCommand` + `artifact-signing-cli`
  (secrets: `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`).
  ([Tauri Windows signing docs](https://v2.tauri.app/distribute/sign/windows/))

### Do NOT buy

- **EV certificates** ($280–400+/yr): zero SmartScreen advantage since Aug 2024, and they
  generally require a registered legal entity.
- **Standard OV certificates** (~$215+/yr): full reputation lag, strictly dominated by all
  options above.

---

## 6. Complete secrets/variables reference

Everything the workflows read. All are optional — when absent, the corresponding signing
steps are skipped and the release is produced unsigned.

| Name | Kind | Platform | Purpose |
|------|------|----------|---------|
| `APPLE_CERTIFICATE` | secret | macOS | base64-encoded Developer ID Application `.p12` |
| `APPLE_CERTIFICATE_PASSWORD` | secret | macOS | password for the `.p12` |
| `APPLE_SIGNING_IDENTITY` | secret | macOS | `Developer ID Application: Name (TEAMID)` |
| `APPLE_API_KEY` | secret | macOS | App Store Connect API key ID (notarization) |
| `APPLE_API_ISSUER` | secret | macOS | App Store Connect issuer ID |
| `APPLE_API_KEY_PATH` | secret | macOS | path to the `.p8` key file |
| `APPLE_ID` | secret | macOS | alternative notarization: Apple ID email |
| `APPLE_PASSWORD` | secret | macOS | alternative notarization: app-specific password |
| `APPLE_TEAM_ID` | secret | macOS | alternative notarization: team ID |
| `SIGNPATH_API_TOKEN` | secret | Windows | SignPath API token |
| `SIGNPATH_ORGANIZATION_ID` | **variable** | Windows | SignPath organization ID; its presence activates the Windows signing steps |
| `GPG_PRIVATE_KEY` | secret | Linux | GPG key used to sign `SHA256SUMS` |

---

## 7. Realistic expectations

Even with everything above in place, understand what signing does and doesn't buy you:
SmartScreen and browser download protection (Edge SmartScreen, Chrome Safe Browsing) keep a
**per-file-hash** reputation component, so the very first downloads of a brand-new release
file can still occasionally show a "not commonly downloaded" warning — even correctly
signed. SignPath Foundation's shared publisher reputation makes this rare in practice, but
it is not contractually zero. The warnings fade as downloads accumulate, and each release
inherits publisher-identity trust from the previous ones. Mitigations that compound over
time: always timestamp signatures (the workflows do), keep the same publisher identity
forever, submit any Defender false positives to
[Microsoft Security Intelligence](https://www.microsoft.com/en-us/wdsi/filesubmission)
(signed submissions get fast-tracked), and consider winget distribution once signed —
repeated clean installs build reputation fast.
