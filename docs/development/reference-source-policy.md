# Read-only reference-source policy

The workspace contains three upstream/reference trees that are inputs to Jak 3
Archipelago development. They are not project-owned working directories.

Snapshot date: **2026-08-07**

## Immutable directories

| Directory | Purpose | Recorded baseline |
| --- | --- | --- |
| `D:\Codex\Jak3\jak-project` | OpenGOAL source, native Jak 3 definitions, and runtime implementation reference. | Git `master`, commit `425f143fc`, clean worktree. |
| `D:\Codex\Jak3\Archipelago` | Archipelago APIs/tests and official Jak and Daxter integration reference. | Git `main`, commit `feab54da`, clean worktree. |
| `D:\Codex\Jak3\openGOAL-decompile` | Read-only Jak 1 and Jak 3 decompiled source snapshots. | No Git metadata; no suspicious Jak 3 AP/mod filenames found in the audit. |

All three directories are **read-only** for this project. Their contents may be
read, searched, compared, and hashed. Do not edit source, apply formatting,
generate caches/build output, install dependencies, install APWorld/GOAL files,
or run a tool that writes into these paths.

`openGOAL-decompile` cannot be certified Git-clean because it is not a Git
checkout in this workspace. Its recorded state is the state supplied to the
project. Treating it as immutable is the only available local preservation
mechanism; restoring it would require obtaining the original snapshot again.

## Project-owned and writable destinations

- `D:\Codex\Jak3\Jak3-AP` owns APWorld, client, mod, tests, build tools, and
  canonical design/development/risk documentation.
- `D:\Codex\Jak3\docs` contains workspace-level redirects and historical
  notes; it is not a second normative specification source.
- `D:\OpenGOAL\active\jak3\data` is the separate active OpenGOAL project that
  the client may install/repair and compile during a smoke test.
- A uniquely named directory below `D:\Codex\Jak3\tmp` may be used for a
  disposable copy when a test inherently writes caches or installed packages.

The distinction between the two OpenGOAL paths is critical:

```text
D:\Codex\Jak3\jak-project          READ ONLY: upstream source reference
D:\OpenGOAL\active\jak3\data      WRITABLE: active mod/compile target
```

Never pass `D:\Codex\Jak3\jak-project` to
`tools\install_opengoal_bridge.ps1`. The `-OpenGoalRoot` argument to
`verify_source_tables.ps1` is safe because that script only reads source.

## Allowed operations

- `Get-Content`, `rg`, `rg --files`, and other read-only inspection.
- `git status`, `git diff`, `git show`, `git log`, and `git rev-parse`.
- `Get-FileHash` and non-writing comparisons.
- `verify_source_tables.ps1 -OpenGoalRoot ...\jak-project`.
- Copying a reference tree to a disposable path, then running writing tests
  only inside the resolved copy.

## Disallowed operations

- `apply_patch` or any source edit under the three reference directories.
- `git commit`, merge, rebase, checkout, reset, clean, or branch changes there
  during normal Jak 3 AP work.
- Running a formatter with write/fix mode.
- Building OpenGOAL inside `jak-project` or adding `archipelago.o` to its DGO.
- Copying `archipelago.gc`, `archipelago-startup.gc`, bootstrap types, an
  APWorld, or generated test data into a reference tree.
- Running `pytest`, package installation, or dependency installation directly
  in `Archipelago`, because those operations can create caches or environment
  files even if source code is unchanged.
- Treating the supplied decompile snapshot as a scratch or generated-output
  directory.

## Audit commands

Use these read-only commands before and after work that consumes the Git-backed
references:

```powershell
$Workspace = "D:\Codex\Jak3"
$JakProject = Join-Path $Workspace "jak-project"
$ArchipelagoReference = Join-Path $Workspace "Archipelago"
$JakSafe = $JakProject.Replace("\", "/")
$ArchipelagoSafe = $ArchipelagoReference.Replace("\", "/")

git -c safe.directory=$JakSafe -C $JakProject status --short --untracked-files=all
git -c safe.directory=$JakSafe -C $JakProject rev-parse --short HEAD

git -c safe.directory=$ArchipelagoSafe -C $ArchipelagoReference `
  status --short --untracked-files=all
git -c safe.directory=$ArchipelagoSafe -C $ArchipelagoReference `
  rev-parse --short HEAD
```

Both status commands must print nothing. A changed commit is not automatically
wrong, but must be an intentional update of the supplied reference baseline,
not a side effect of Jak 3 AP work.

Because the decompile tree lacks Git metadata, perform a narrow contamination
scan without claiming it proves byte-for-byte provenance:

```powershell
rg --files (Join-Path $Workspace "openGOAL-decompile") |
  rg -i '(^|[\\/])(archipelago|jak3-ap)|archipelago\.(gc|o)$'
```

No result is expected. Source-content searches for research are still allowed;
this command checks only suspicious project-owned filenames.

## Disposable Archipelago test copy

Some Archipelago tests import custom worlds and write caches. Use a unique copy
below the workspace's `tmp` boundary:

```powershell
$Workspace = "D:\Codex\Jak3"
$ArchipelagoReference = Join-Path $Workspace "Archipelago"
$TestRoot = Join-Path $Workspace (
  "tmp\Archipelago-jak3-test-" + [guid]::NewGuid().ToString("N")
)
Copy-Item -LiteralPath $ArchipelagoReference -Destination $TestRoot -Recurse
```

Before deleting the copy, resolve and verify both paths:

```powershell
$ResolvedTmp = (Resolve-Path (Join-Path $Workspace "tmp")).Path.TrimEnd("\") + "\"
$ResolvedTest = (Resolve-Path -LiteralPath $TestRoot).Path
if (-not $ResolvedTest.StartsWith(
  $ResolvedTmp,
  [System.StringComparison]::OrdinalIgnoreCase
)) {
  throw "Refusing to remove a test copy outside the workspace tmp directory."
}
Remove-Item -LiteralPath $ResolvedTest -Recurse -Force
```

This cleanup must never target the workspace root or any reference tree.

## 2026-08-05 contamination audit and restoration

The audit that introduced this policy found two changes under `jak-project`:

1. `goal_src/jak3/dgos/game.gd` contained one added `"archipelago.o"` entry
   immediately after `"task-control.o"`.
2. `goal_src/jak3/pc/features/archipelago.gc` was an untracked Jak 3 AP bridge
   file.

Both were unambiguously project integration artifacts and were removed. Git
then reported a clean `jak-project` worktree at `425f143fc`. No source file in
`Archipelago` was changed, its checkout remained clean at `feab54da`, and its
`custom_worlds` directory contained no Jak 3 entry. `openGOAL-decompile` had no
suspicious AP/mod filename, but cannot be compared with Git for the reason
described above.

Track recurrence and prevention under `R-017` in
[`../JAK3_AP_RISKS.md`](../JAK3_AP_RISKS.md).
