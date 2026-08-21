[CmdletBinding()]
param(
    [ValidateSet("All", "Static", "Package", "Tests")]
    [string] $Phase = "All",

    [string] $ArchipelagoPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path -LiteralPath "$PSScriptRoot\..").Path

function Invoke-PythonCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Label,

        [Parameter(Mandatory = $true)]
        [string[]] $Arguments
    )

    Write-Host "==> $Label"
    & python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE."
    }
}

function Assert-RepositoryContract {
    $requiredFiles = @(
        ".gitattributes",
        "AGENTS.md",
        "config/templates/Jak3.yaml",
        "docs/design/progression-and-logic.md",
        "docs/development/Project-Milestones-Revised.md",
        "mod/opengoal/bridge-modules.json"
    )

    foreach ($relativePath in $requiredFiles) {
        $path = Join-Path $repositoryRoot $relativePath
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Required repository contract file is missing: $relativePath"
        }
    }

    $attributesPath = Join-Path $repositoryRoot ".gitattributes"
    $attributes = Get-Content -LiteralPath $attributesPath
    if ($attributes -notcontains "* text=auto eol=lf") {
        throw ".gitattributes must keep the canonical '* text=auto eol=lf' policy."
    }
}

function Invoke-StaticChecks {
    $lintArguments = @(
        "-m", "ruff", "check", "--ignore", "E402",
        "worlds/jak3",
        "tests",
        "tools/generate_milestone_10_fixture.py",
        "tools/run_milestone_11_spikes.py"
    )
    Invoke-PythonCommand -Label "Ruff lint" -Arguments $lintArguments

    $formatTargets = @(
        "worlds/jak3/canonical.py",
        "worlds/jak3/versions.py",
        "worlds/jak3/legacy_ids.py",
        "worlds/jak3/registry.py",
        "worlds/jak3/slot_data.py",
        "worlds/jak3/persistence.py",
        "worlds/jak3/location_outbox.py",
        "worlds/jak3/received_items.py",
        "worlds/jak3/client.py",
        "worlds/jak3/agents/bridge_manifest.py",
        "worlds/jak3/agents/diagnostics.py",
        "worlds/jak3/agents/launcher.py",
        "worlds/jak3/agents/protocol.py",
        "worlds/jak3/agents/repl_client.py",
        "tests/test_registry.py",
        "tests/test_slot_data.py",
        "tests/test_persistence.py",
        "tests/test_location_outbox.py",
        "tests/test_milestone_10_fixture.py",
        "tests/test_milestone_11_spikes.py",
        "tests/test_bridge_manifest.py",
        "tests/test_client.py",
        "tests/test_diagnostics.py",
        "tests/test_launcher.py",
        "tests/test_package.py",
        "tests/test_protocol_v3.py",
        "tests/test_received_items.py",
        "tests/test_tools.py",
        "tests/test_ci.py",
        "tools/generate_milestone_10_fixture.py",
        "tools/run_milestone_11_spikes.py"
    )
    $formatArguments = @("-m", "ruff", "format", "--check") + $formatTargets
    Invoke-PythonCommand -Label "Ruff format" -Arguments $formatArguments

    $mypyTargets = @(
        "worlds/jak3/canonical.py",
        "worlds/jak3/versions.py",
        "worlds/jak3/legacy_ids.py",
        "worlds/jak3/registry.py",
        "worlds/jak3/slot_data.py",
        "worlds/jak3/persistence.py",
        "worlds/jak3/location_outbox.py",
        "worlds/jak3/received_items.py",
        "worlds/jak3/client.py",
        "worlds/jak3/agents/bridge_manifest.py",
        "worlds/jak3/agents/diagnostics.py",
        "worlds/jak3/agents/launcher.py",
        "worlds/jak3/agents/protocol.py",
        "tools/run_milestone_11_spikes.py"
    )
    $mypyArguments = @(
        "-m", "mypy",
        "--ignore-missing-imports",
        "--follow-imports=skip"
    ) + $mypyTargets
    Invoke-PythonCommand -Label "mypy" -Arguments $mypyArguments
}

function Invoke-PackageBuild {
    Write-Host "==> APWorld package build"
    & (Join-Path $PSScriptRoot "build_apworld.ps1")
}

function Invoke-PackagedTests {
    if ([string]::IsNullOrWhiteSpace($ArchipelagoPath)) {
        throw "-ArchipelagoPath is required for the Tests and All phases. Use a disposable Archipelago checkout."
    }

    $archipelagoRoot = (Resolve-Path -LiteralPath $ArchipelagoPath).Path
    foreach ($relativePath in @("BaseClasses.py", "worlds")) {
        if (-not (Test-Path -LiteralPath (Join-Path $archipelagoRoot $relativePath))) {
            throw "Archipelago test checkout is missing ${relativePath}: $archipelagoRoot"
        }
    }

    $artifact = Join-Path $repositoryRoot "dist\jak3.apworld"
    if (-not (Test-Path -LiteralPath $artifact -PathType Leaf)) {
        throw "The APWorld artifact is missing. Run the Package phase before Tests."
    }

    $customWorlds = Join-Path $archipelagoRoot "custom_worlds"
    New-Item -ItemType Directory -Path $customWorlds -Force | Out-Null
    Copy-Item -LiteralPath $artifact -Destination (Join-Path $customWorlds "jak3.apworld") -Force

    $testRoot = (Resolve-Path -LiteralPath (Join-Path $repositoryRoot "tests")).Path
    $env:AP_TEST_WORLDS = "jak3"
    $env:SKIP_REQUIREMENTS_UPDATE = "1"
    Push-Location $archipelagoRoot
    try {
        Invoke-PythonCommand -Label "Packaged pytest suite" -Arguments @(
            "-m", "pytest", $testRoot, "-q"
        )
    }
    finally {
        Pop-Location
    }
}

Assert-RepositoryContract

Push-Location $repositoryRoot
try {
    if ($Phase -in @("All", "Static")) {
        Invoke-StaticChecks
    }
    if ($Phase -in @("All", "Package")) {
        Invoke-PackageBuild
    }
    if ($Phase -in @("All", "Tests")) {
        Invoke-PackagedTests
    }
}
finally {
    Pop-Location
}
