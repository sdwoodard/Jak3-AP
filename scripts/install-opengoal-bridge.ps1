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
$source = Join-Path $PSScriptRoot "..\opengoal\archipelago\archipelago.gc"
$source = (Resolve-Path -LiteralPath $source).Path

if (-not (Test-Path -LiteralPath $projectFile -PathType Leaf)) {
    throw "This does not look like an OpenGOAL Jak 3 repository: $projectFile was not found."
}
if (-not (Test-Path -LiteralPath $destinationDirectory -PathType Container)) {
    throw "The Jak 3 feature source directory was not found: $destinationDirectory"
}

Copy-Item -LiteralPath $source -Destination $destinationSource -Force

$projectText = [System.IO.File]::ReadAllText($projectFile)
$objectLine = '  "archipelago.o"'
if ($projectText -notmatch '(?m)^[ \t]*"archipelago\.o"[ \t]*$') {
    $markerPattern = '(?m)^([ \t]*"task-control\.o"[ \t]*)$'
    $markerMatches = [regex]::Matches($projectText, $markerPattern)
    if ($markerMatches.Count -ne 1) {
        throw "Expected exactly one task-control.o entry in $projectFile; found $($markerMatches.Count)."
    }
    $projectText = [regex]::Replace(
        $projectText,
        $markerPattern,
        ('$1' + [Environment]::NewLine + $objectLine),
        1
    )
    [System.IO.File]::WriteAllText(
        $projectFile,
        $projectText,
        [System.Text.UTF8Encoding]::new($false)
    )
}

Write-Host "Installed Jak 3 Archipelago bridge source: $destinationSource"
Write-Host "Registered archipelago.o immediately after task-control.o in: $projectFile"
Write-Host "Open a fresh Jak 3 goalc and run (mi)."
Write-Host "Keep goalc and the Debug game open; Jak 3 Client /repl connect will attach and load the bridge."
