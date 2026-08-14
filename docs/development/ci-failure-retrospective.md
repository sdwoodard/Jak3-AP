# CI failure retrospective

Date: 2026-08-14

GitHub Actions recorded 15 CI runs through commit `9914168`: eight passed and
seven failed. The failures were deterministic rather than flaky. Public run
metadata, the follow-up diffs, the supplied Milestone 10 log, and local
reproduction of the two missing-file failures identify four recurring classes.

| Failed commit(s) | Failed gate | Cause | Corrective commit |
| --- | --- | --- | --- |
| `0cdc04e` | Packaged tests | The standalone installer depended on `Get-FileHash`, which was unavailable in the constrained PowerShell test host. | `85afa02` |
| `e0b2a8d` | APWorld build | Manifest validation assumed Windows PowerShell 5.1's `Int32` JSON numbers; PowerShell Core returned `Int64`. | `4a65dbe` |
| `4a65dbe`, `d028dd6` | Packaged tests | The GOAL event parser assumed LF and rejected the Windows runner's CRLF checkout. | `1cf263d` |
| `b0fd45c`, `e0c35ef` | Packaged tests | `AGENTS.md`, a tested canonical source, had been deleted. Both historical suites reproduce with one failure at `test_canonical_sources_are_present_in_a_standalone_checkout`. | `d14ceaf` |
| `e6b66ec` | Packaged tests | New multiline GOAL source assertions again assumed LF while reading raw CRLF bytes. | `9914168` |

The dominant process failure was not missing CI coverage: the existing suite
caught every issue. Changes were pushed directly to `main` without first
running the complete packaged gate in an equivalent checkout, and on two
occasions another commit was pushed while the same failure was still present.

The repository now uses these preventive controls:

- `.gitattributes` fixes text checkouts to canonical LF, and the manifest suite
  rejects carriage returns in every raw source-set hash input.
- `tools/run_ci_checks.ps1` is the single implementation for local and hosted
  lint, format, type, package, and packaged-test gates.
- The preflight rejects missing normative sources and removal of the LF policy
  before running slower checks.
- `AGENTS.md` requires the complete preflight before push and directs agents to
  use a feature branch when the GitHub runner cannot be reproduced locally.
- CI uses current Node-runtime GitHub Actions instead of deprecated action
  generations.

Repository settings should additionally require the `python-apworld` check on
`main`. Branch protection is intentionally an external administrator action;
it cannot be enforced by a committed workflow file.
