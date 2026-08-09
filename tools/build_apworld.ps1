param(
    [string]$OutputDirectory = "$PSScriptRoot\..\dist"
)

$ErrorActionPreference = "Stop"

function Assert-ExactJsonFields {
    param(
        [Parameter(Mandatory = $true)]
        [object] $Value,
        [Parameter(Mandatory = $true)]
        [string[]] $Expected,
        [Parameter(Mandatory = $true)]
        [string] $Label
    )

    $actual = @($Value.PSObject.Properties.Name)
    if ($actual.Count -ne $Expected.Count) {
        throw "$Label must contain exactly: $($Expected -join ', ')."
    }
    foreach ($field in $Expected) {
        if (-not ($actual -ccontains $field)) {
            throw "$Label must contain exactly: $($Expected -join ', ')."
        }
    }
}

$repositoryRoot = (Resolve-Path "$PSScriptRoot\..").Path
$worldSource = Join-Path $repositoryRoot "worlds\jak3"
$bridgeRoot = Join-Path $repositoryRoot "mod\opengoal"
$bridgeManifestPath = Join-Path $bridgeRoot "bridge-modules.json"
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
if (-not (Test-Path -LiteralPath $bridgeManifestPath -PathType Leaf)) {
    throw "OpenGOAL bridge manifest not found: $bridgeManifestPath"
}
if (-not (Test-Path -LiteralPath $iconSource -PathType Leaf)) {
    throw "Jak 3 launcher icon not found: $iconSource"
}

$bridgeManifest = Get-Content -LiteralPath $bridgeManifestPath -Raw | ConvertFrom-Json
Assert-ExactJsonFields $bridgeManifest `
    @("manifest_version", "source_set_format", "object_anchor", "modules") `
    "OpenGOAL bridge manifest"
if ($bridgeManifest.manifest_version -isnot [int] -or
    $bridgeManifest.source_set_format -isnot [string] -or
    $bridgeManifest.object_anchor -isnot [string] -or
    $bridgeManifest.modules -isnot [System.Array]) {
    throw "OpenGOAL bridge manifest fields have invalid JSON scalar types."
}
if ($bridgeManifest.manifest_version -ne 1 -or
    $bridgeManifest.source_set_format -ne "jak3-bridge-source-set-v1" -or
    $bridgeManifest.object_anchor -ne "task-control.o") {
    throw "Unsupported OpenGOAL bridge manifest contract."
}
$expectedModules = @(
    @{ name = "startup"; order = 10; phase = "pre_mi"; source = "goal_src/jak3/pc/features/archipelago-startup.gc"; resource = "assets/opengoal/archipelago-startup.gc"; destination = "goal_src/jak3/pc/features/archipelago-startup.gc"; object = $null },
    @{ name = "control"; order = 20; phase = "bridge"; source = "goal_src/jak3/pc/features/archipelago.gc"; resource = "assets/opengoal/archipelago.gc"; destination = "goal_src/jak3/pc/features/archipelago.gc"; object = "archipelago.o" },
    @{ name = "diagnostics"; order = 30; phase = "bridge"; source = "goal_src/jak3/pc/features/archipelago-diagnostics.gc"; resource = "assets/opengoal/archipelago-diagnostics.gc"; destination = "goal_src/jak3/pc/features/archipelago-diagnostics.gc"; object = "archipelago-diagnostics.o" }
)
$declaredBridgeModules = @($bridgeManifest.modules)
foreach ($module in $declaredBridgeModules) {
    Assert-ExactJsonFields $module `
        @("name", "order", "phase", "source", "resource", "destination", "object") `
        "OpenGOAL bridge module"
    if ($module.name -isnot [string] -or $module.order -isnot [int] -or
        $module.phase -isnot [string] -or $module.source -isnot [string] -or
        $module.resource -isnot [string] -or $module.destination -isnot [string] -or
        ($null -ne $module.object -and $module.object -isnot [string])) {
        throw "OpenGOAL bridge module fields have invalid JSON scalar types."
    }
}
$bridgeModules = @($bridgeManifest.modules | Sort-Object order)
if ($bridgeModules.Count -ne $expectedModules.Count) {
    throw "Bridge manifest must declare exactly $($expectedModules.Count) modules."
}
$uniqueFields = @("name", "order", "source", "resource", "destination", "object")
foreach ($field in $uniqueFields) {
    $values = @($bridgeModules | ForEach-Object { $_.$field } | Where-Object { $null -ne $_ })
    if (@($values | Select-Object -Unique).Count -ne $values.Count) {
        throw "Bridge manifest contains duplicate $field values."
    }
}
for ($index = 0; $index -lt $bridgeModules.Count; $index++) {
    $module = $bridgeModules[$index]
    $expected = $expectedModules[$index]
    Assert-ExactJsonFields $module `
        @("name", "order", "phase", "source", "resource", "destination", "object") `
        "OpenGOAL bridge module $index"
    if ($module.name -ne $expected.name -or $module.order -ne $expected.order -or
        $module.phase -ne $expected.phase -or $module.source -ne $expected.source -or
        $module.resource -ne $expected.resource -or
        $module.destination -ne $expected.destination -or
        $module.object -ne $expected.object) {
        throw "Bridge manifest modules are not in the canonical version 1 order."
    }
    foreach ($field in @("source", "resource", "destination")) {
        $value = [string]$module.$field
        if ([string]::IsNullOrWhiteSpace($value) -or $value.Contains("\") -or
            [System.IO.Path]::IsPathRooted($value) -or $value.Split("/").Contains("..")) {
            throw "Unsafe bridge module $field path: $value"
        }
    }
    if ($module.source -ne $module.destination) {
        throw "Bridge module source and destination must match for $($module.name)."
    }
    if ([System.IO.Path]::GetFileName($module.source) -ne
        [System.IO.Path]::GetFileName($module.resource)) {
        throw "Bridge module source and resource names must match for $($module.name)."
    }
    $moduleSource = Join-Path $bridgeRoot $module.source.Replace("/", "\")
    if (-not (Test-Path -LiteralPath $moduleSource -PathType Leaf)) {
        throw "OpenGOAL bridge module source not found: $moduleSource"
    }
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
    Copy-Item -LiteralPath $bridgeManifestPath -Destination (Join-Path $stagedBridgeDirectory "bridge-modules.json")
    foreach ($module in $bridgeModules) {
        $moduleSource = Join-Path $bridgeRoot $module.source.Replace("/", "\")
        $resourcePath = Join-Path $stagingRoot ("jak3\" + $module.resource.Replace("/", "\"))
        $resourceDirectory = Split-Path -Parent $resourcePath
        New-Item -ItemType Directory -Path $resourceDirectory -Force | Out-Null
        Copy-Item -LiteralPath $moduleSource -Destination $resourcePath
    }
    $declaredResources = @($bridgeModules | ForEach-Object { $_.resource })
    Get-ChildItem -LiteralPath $stagedWorld -Filter "archipelago-*.gc" -File -Recurse |
        ForEach-Object {
            $resource = $_.FullName.Substring($stagedWorld.Length).TrimStart("\", "/").Replace("\", "/")
            if ($resource -notin $declaredResources) {
                throw "Packaged OpenGOAL module is undeclared: $resource"
            }
        }
    # APWorld container metadata is generated at packaging time. Keep these
    # fields out of the source manifest, as required by the APWorld spec.
    $stagedManifestPath = Join-Path $stagingRoot "jak3\archipelago.json"
    $manifest = Get-Content -LiteralPath $stagedManifestPath -Raw | ConvertFrom-Json
    $manifest | Add-Member -NotePropertyName "version" -NotePropertyValue $containerVersion -Force
    $manifest | Add-Member -NotePropertyName "compatible_version" -NotePropertyValue $compatibleVersion -Force
    $manifestJson = $manifest | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($stagedManifestPath, $manifestJson, [System.Text.UTF8Encoding]::new($false))

    # Compress-Archive stamps generated directory entries with the staging
    # time, which makes byte-identical inputs produce different APWorlds.
    # Write the small archive explicitly in canonical path order with one
    # fixed ZIP timestamp instead.
    Add-Type -AssemblyName System.IO.Compression
    $fixedZipTime = [System.DateTimeOffset]::new(
        2000, 1, 1, 0, 0, 0, [System.TimeSpan]::Zero
    )
    $zipStream = [System.IO.File]::Open(
        $zipPath,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None
    )
    $zipArchive = $null
    try {
        $zipArchive = [System.IO.Compression.ZipArchive]::new(
            $zipStream,
            [System.IO.Compression.ZipArchiveMode]::Create,
            $false
        )
        $assetsEntry = $zipArchive.CreateEntry("jak3/assets/")
        $assetsEntry.LastWriteTime = $fixedZipTime
        $stagedFiles = Get-ChildItem -LiteralPath $stagedWorld -File -Recurse |
            Sort-Object { $_.FullName.Substring($stagedWorld.Length).Replace("\", "/") }
        foreach ($file in $stagedFiles) {
            $relativePath = $file.FullName.Substring($stagedWorld.Length).TrimStart("\", "/")
            $entryName = "jak3/" + $relativePath.Replace("\", "/")
            $entry = $zipArchive.CreateEntry(
                $entryName,
                [System.IO.Compression.CompressionLevel]::Optimal
            )
            $entry.LastWriteTime = $fixedZipTime
            $sourceStream = [System.IO.File]::OpenRead($file.FullName)
            $entryStream = $entry.Open()
            try {
                $sourceStream.CopyTo($entryStream)
            }
            finally {
                $entryStream.Dispose()
                $sourceStream.Dispose()
            }
        }
    }
    finally {
        if ($null -ne $zipArchive) {
            $zipArchive.Dispose()
        }
        else {
            $zipStream.Dispose()
        }
    }
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
        "jak3/persistence.py",
        "jak3/agents/launcher.py",
        "jak3/agents/diagnostics.py",
        "jak3/agents/bridge_manifest.py",
        "jak3/agents/protocol.py",
        "jak3/assets/opengoal/bridge-modules.json",
        "jak3/assets/opengoal/archipelago-startup.gc",
        "jak3/assets/opengoal/archipelago.gc",
        "jak3/assets/opengoal/archipelago-diagnostics.gc",
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
