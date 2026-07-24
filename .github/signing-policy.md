# Code Signing Policy

**Project:** File Converter Pro
**Repository:** <https://github.com/dequaviousthe7th/file-converter>
**License:** MIT (OSI-approved), no dual licensing, no proprietary components

Free code signing on Windows is provided by [SignPath.io](https://signpath.io),
certificate by [SignPath Foundation](https://signpath.org).

## How releases are built

- All release binaries are built **exclusively by GitHub Actions** from the
  source code in this repository, using the workflow at
  [`.github/workflows/release.yml`](workflows/release.yml).
- Builds are triggered only by version tags (`v*`) pushed by a maintainer, or
  by a maintainer manually dispatching the Release workflow.
- No manually or locally built binaries are ever submitted for signing.
- Signing requests are submitted automatically by the Release workflow via
  `signpath/github-action-submit-signing-request`, so every request is
  traceable to the exact commit, tag, and workflow run that produced the
  artifact (SignPath origin verification).

## Who may request and approve signing

| Role | Person |
|---|---|
| Author / Committer | [@dequaviousthe7th](https://github.com/dequaviousthe7th) (project owner and sole maintainer) |
| Reviewer | [@dequaviousthe7th](https://github.com/dequaviousthe7th) |
| Approver | [@dequaviousthe7th](https://github.com/dequaviousthe7th) |

- Only the repository owner can push tags or dispatch the Release workflow,
  and therefore only the owner can originate signing requests.
- **Every signing request requires a manual approval** by the approver in the
  SignPath web UI before a signature is issued. Unapproved or unexpected
  requests are denied.
- Multi-factor authentication is enabled on the GitHub and SignPath accounts
  involved in the release process.

## What gets signed and where it is distributed

- Signed artifact: the Windows NSIS installer (`File Converter Pro
  *-setup.exe`) produced by the Release workflow.
- Signed binaries are distributed **only** through the
  [GitHub Releases page](https://github.com/dequaviousthe7th/file-converter/releases)
  of this repository.

## Privacy commitment

This program will not transfer any information to other networked systems
unless specifically requested by the user or the person installing or
operating it. Conversions run entirely locally on the user's machine.

## Contact

Questions about this policy, the release process, or a specific signed
release: please open an issue at
<https://github.com/dequaviousthe7th/file-converter/issues>.
