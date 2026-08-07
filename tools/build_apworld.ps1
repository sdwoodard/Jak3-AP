param(
    [string]$OutputDirectory = "$PSScriptRoot\..\dist"
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path "$PSScriptRoot\..").Path
$worldSource = Join-Path $repositoryRoot "worlds\jak3"
$bridgeSource = Join-Path $repositoryRoot "mod\opengoal\goal_src\jak3\pc\features\archipelago.gc"
$startupSource = Join-Path $repositoryRoot "mod\opengoal\goal_src\jak3\pc\features\archipelago-startup.gc"
$iconSource = Join-Path $worldSource "icons\jak3-logo.png"
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputDirectory)
$artifact = Join-Path $resolvedOutput "jak3.apworld"
$containerVersion = 7
$compatibleVersion = 7
$sourceManifest = Get-Content -LiteralPath (Join-Path $worldSource "archipelago.json") -Raw | ConvertFrom-Json
$expectedWorldVersion = $sourceManifest.world_version

if (-not (Test-Path -LiteralPath $worldSource -PathType Container)) {
    throw "APWorld source directory not found: $worldSource"
}
if (-not (Test-Path -LiteralPath $bridgeSource -PathType Leaf)) {
    throw "OpenGOAL bridge source not found: $bridgeSource"
}
if (-not (Test-Path -LiteralPath $startupSource -PathType Leaf)) {
    throw "OpenGOAL startup overlay source not found: $startupSource"
}
if (-not (Test-Path -LiteralPath $iconSource -PathType Leaf)) {
    throw "Jak 3 launcher icon not found: $iconSource"
}

# The launcher renders this asset over its own background. Reject an opaque or
# unexpectedly sized replacement before it reaches a release archive.
Add-Type -AssemblyName System.Drawing
$icon = [System.Drawing.Bitmap]::new($iconSource)
try {
    if ($icon.Width -ne 256 -or $icon.Height -ne 256) {
        throw "Jak 3 launcher icon must be 256x256; got $($icon.Width)x$($icon.Height)."
    }
    $hasTransparency = $false
    for ($y = 0; $y -lt $icon.Height -and -not $hasTransparency; $y++) {
        for ($x = 0; $x -lt $icon.Width; $x++) {
            if ($icon.GetPixel($x, $y).A -lt 255) {
                $hasTransparency = $true
                break
            }
        }
    }
    if (-not $hasTransparency) {
        throw "Jak 3 launcher icon must contain transparent pixels."
    }
}
finally {
    $icon.Dispose()
}

New-Item -ItemType Directory -Path $resolvedOutput -Force | Out-Null

$stagingRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("jak3-ap-" + [guid]::NewGuid().ToString("N"))
$zipPath = Join-Path $resolvedOutput ("jak3-" + [guid]::NewGuid().ToString("N") + ".zip")
New-Item -ItemType Directory -Path $stagingRoot | Out-Null
try {
    Copy-Item -LiteralPath $worldSource -Destination $stagingRoot -Recurse
    $stagedWorld = Join-Path $stagingRoot "jak3"
    Get-ChildItem -LiteralPath $stagedWorld -File -Recurse |
        Where-Object { $_.Extension -in @(".pyc", ".pyo") } |
        ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force }
    Get-ChildItem -LiteralPath $stagedWorld -Directory -Filter "__pycache__" -Recurse |
        Sort-Object FullName -Descending |
        ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force }
    $stagedBridgeDirectory = Join-Path $stagingRoot "jak3\assets\opengoal"
    New-Item -ItemType Directory -Path $stagedBridgeDirectory -Force | Out-Null
    Copy-Item -LiteralPath $bridgeSource -Destination (Join-Path $stagedBridgeDirectory "archipelago.gc")
    Copy-Item -LiteralPath $startupSource -Destination (Join-Path $stagedBridgeDirectory "archipelago-startup.gc")
    # APWorld container metadata is generated at packaging time. Keep these
    # fields out of the source manifest, as required by the APWorld spec.
    $stagedManifestPath = Join-Path $stagingRoot "jak3\archipelago.json"
    $manifest = Get-Content -LiteralPath $stagedManifestPath -Raw | ConvertFrom-Json
    $manifest | Add-Member -NotePropertyName "version" -NotePropertyValue $containerVersion -Force
    $manifest | Add-Member -NotePropertyName "compatible_version" -NotePropertyValue $compatibleVersion -Force
    $manifestJson = $manifest | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($stagedManifestPath, $manifestJson, [System.Text.UTF8Encoding]::new($false))

    Compress-Archive -LiteralPath (Join-Path $stagingRoot "jak3") -DestinationPath $zipPath -CompressionLevel Optimal
    # Windows scanners and launchers can briefly retain a handle to the old
    # archive. Retry a bounded replacement without deleting the last known-good
    # artifact first.
    $installed = $false
    for ($attempt = 1; $attempt -le 10 -and -not $installed; $attempt++) {
        try {
            Copy-Item -LiteralPath $zipPath -Destination $artifact -Force -ErrorAction Stop
            $installed = $true
        }
        catch {
            if ($attempt -eq 10) {
                throw
            }
            Start-Sleep -Milliseconds 200
        }
    }
}
finally {
    if (Test-Path -LiteralPath $stagingRoot) {
        Remove-Item -LiteralPath $stagingRoot -Recurse -Force
    }
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
}

# Validate the same manifest contract APWorldContainer.read_contents enforces
# before returning an artifact that could silently fall back to version 0.0.0.
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::OpenRead($artifact)
try {
    $manifestEntry = $archive.Entries |
        Where-Object { $_.FullName.Replace("\", "/") -eq "jak3/archipelago.json" } |
        Select-Object -First 1
    if (-not $manifestEntry) {
        throw "Packaged APWorld is missing jak3/archipelago.json."
    }
    $requiredEntries = @(
        "jak3/agents/launcher.py",
        "jak3/agents/diagnostics.py",
        "jak3/agents/protocol.py",
        "jak3/assets/opengoal/archipelago-startup.gc",
        "jak3/assets/opengoal/archipelago.gc",
        "jak3/icons/jak3-logo.png"
    )
    foreach ($requiredEntry in $requiredEntries) {
        $found = $archive.Entries | Where-Object {
            $_.FullName.Replace("\", "/") -eq $requiredEntry
        } | Select-Object -First 1
        if (-not $found) {
            throw "Packaged APWorld is missing $requiredEntry."
        }
    }
    $reader = [System.IO.StreamReader]::new($manifestEntry.Open())
    try {
        $packagedManifest = $reader.ReadToEnd() | ConvertFrom-Json
    }
    finally {
        $reader.Dispose()
    }
    if ($packagedManifest.game -ne "Jak 3") {
        throw "Packaged manifest has the wrong game: $($packagedManifest.game)"
    }
    if ($packagedManifest.world_version -ne $expectedWorldVersion) {
        throw "Packaged manifest has the wrong world version: $($packagedManifest.world_version)"
    }
    if ($packagedManifest.version -ne $containerVersion -or
        $packagedManifest.compatible_version -ne $compatibleVersion) {
        throw "Packaged manifest is missing APWorld container version $containerVersion metadata."
    }
}
finally {
    $archive.Dispose()
}

Write-Output $artifact
