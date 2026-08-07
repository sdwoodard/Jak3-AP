[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $OpenGoalRepository
)

$ErrorActionPreference = "Stop"

$repository = (Resolve-Path -LiteralPath $OpenGoalRepository).Path
$projectFile = Join-Path $repository "goal_src\jak3\dgos\game.gd"
$destinationDirectory = Join-Path $repository "goal_src\jak3\pc\features"
$destinationSource = Join-Path $destinationDirectory "archipelago.gc"
$source = Join-Path $PSScriptRoot "..\mod\opengoal\goal_src\jak3\pc\features\archipelago.gc"
$source = (Resolve-Path -LiteralPath $source).Path

if (-not (Test-Path -LiteralPath $projectFile -PathType Leaf)) {
    throw "This does not look like an OpenGOAL Jak 3 repository: $projectFile was not found."
}
if (-not (Test-Path -LiteralPath $destinationDirectory -PathType Container)) {
    throw "The Jak 3 feature source directory was not found: $destinationDirectory"
}

$projectText = [System.IO.File]::ReadAllText($projectFile)
$objectLine = '  "archipelago.o"'
$markerPattern = '(?m)^([ \t]*"task-control\.o"[ \t]*)(?=\r?$)'
$bridgePattern = '(?m)^[ \t]*"archipelago\.o"[ \t]*(?=\r?$)'
$markerMatches = [regex]::Matches($projectText, $markerPattern)
$bridgeMatches = [regex]::Matches($projectText, $bridgePattern)
if ($markerMatches.Count -ne 1) {
    throw "Expected exactly one task-control.o entry in $projectFile; found $($markerMatches.Count)."
}
if ($bridgeMatches.Count -gt 1) {
    throw "Expected at most one archipelago.o entry in $projectFile; found $($bridgeMatches.Count)."
}
if ($bridgeMatches.Count -eq 1 -and $bridgeMatches[0].Index -lt $markerMatches[0].Index) {
    throw "archipelago.o must load after task-control.o in $projectFile."
}

$projectUpdated = $bridgeMatches.Count -eq 0
if ($projectUpdated) {
    $projectText = [regex]::Replace(
        $projectText,
        $markerPattern,
        ('$1' + [Environment]::NewLine + $objectLine),
        1
    )
}

Copy-Item -LiteralPath $source -Destination $destinationSource -Force

if ($projectUpdated) {
    [System.IO.File]::WriteAllText(
        $projectFile,
        $projectText,
        [System.Text.UTF8Encoding]::new($false)
    )
}

Write-Host "Installed Jak 3 Archipelago bridge source: $destinationSource"
Write-Host "Registered archipelago.o immediately after task-control.o in: $projectFile"
Write-Host "Bridge installation complete."
Write-Host "Launching Jak 3 Client now starts Debug gk/goalc, recompiles, and verifies protocol 2."
