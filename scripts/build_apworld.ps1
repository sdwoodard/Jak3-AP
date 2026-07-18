param(
    [string]$OutputDirectory = "$PSScriptRoot\..\dist"
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path "$PSScriptRoot\..").Path
$worldSource = Join-Path $repositoryRoot "jak3"
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputDirectory)
$artifact = Join-Path $resolvedOutput "jak3.apworld"
$containerVersion = 7
$compatibleVersion = 7
$sourceManifest = Get-Content -LiteralPath (Join-Path $worldSource "archipelago.json") -Raw | ConvertFrom-Json
$expectedWorldVersion = $sourceManifest.world_version

if (-not (Test-Path -LiteralPath $worldSource -PathType Container)) {
    throw "APWorld source directory not found: $worldSource"
}

New-Item -ItemType Directory -Path $resolvedOutput -Force | Out-Null

$stagingRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("jak3-ap-" + [guid]::NewGuid().ToString("N"))
$zipPath = Join-Path $resolvedOutput ("jak3-" + [guid]::NewGuid().ToString("N") + ".zip")
New-Item -ItemType Directory -Path $stagingRoot | Out-Null
try {
    Copy-Item -LiteralPath $worldSource -Destination $stagingRoot -Recurse
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
