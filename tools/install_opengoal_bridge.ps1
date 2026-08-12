[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $OpenGoalRepository
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

function Test-JsonIntegerScalar {
    param(
        [AllowNull()]
        [object] $Value
    )

    # ConvertFrom-Json uses Int32 in Windows PowerShell 5.1 and Int64 in the
    # PowerShell Core host used by CI. Accept only those integral JSON number
    # representations; strings, booleans, and fractional numbers still fail.
    return ($Value -is [int] -or $Value -is [long])
}

$repository = (Resolve-Path -LiteralPath $OpenGoalRepository).Path
$projectFile = Join-Path $repository "goal_src\jak3\dgos\game.gd"
$destinationDirectory = Join-Path $repository "goal_src\jak3\pc\features"
$reloadMarker = Join-Path $destinationDirectory ".archipelago-reload-required"
$bridgeRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\mod\opengoal")).Path
$manifestSource = Join-Path $bridgeRoot "bridge-modules.json"
$manifestDestination = Join-Path $destinationDirectory "archipelago-bridge-modules.json"
$installLockDirectory = Join-Path $destinationDirectory ".archipelago-install.lock"

function Get-Sha256Hex {
    param(
        [Parameter(Mandatory = $true)]
        [string] $LiteralPath
    )

    # Get-FileHash is supplied by Microsoft.PowerShell.Utility, which is not
    # available in every PowerShell host used by Archipelago's Windows tests.
    # Use the framework crypto API so the standalone installer has no module
    # dependency.
    $stream = [System.IO.File]::OpenRead($LiteralPath)
    $algorithm = $null
    try {
        $algorithm = [System.Security.Cryptography.SHA256]::Create()
        $digest = $algorithm.ComputeHash($stream)
        return [System.BitConverter]::ToString($digest).Replace("-", "").ToLowerInvariant()
    }
    finally {
        if ($null -ne $algorithm) {
            $algorithm.Dispose()
        }
        $stream.Dispose()
    }
}

function Get-Sha256Text {
    param([Parameter(Mandatory = $true)][string] $Text)
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($Text)
        return [System.BitConverter]::ToString($algorithm.ComputeHash($bytes)).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $algorithm.Dispose()
    }
}

function Get-ProcessStartIdentity {
    param([Parameter(Mandatory = $true)][int] $ProcessId)

    $process = $null
    try {
        $process = Get-Process -Id $ProcessId -ErrorAction Stop
        if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
            $fileTime = $process.StartTime.ToUniversalTime().ToFileTimeUtc()
            return "windows-filetime:$fileTime"
        }

        $statPath = "/proc/$ProcessId/stat"
        if (Test-Path -LiteralPath $statPath -PathType Leaf) {
            $stat = [System.IO.File]::ReadAllText($statPath)
            $closeParen = $stat.LastIndexOf(")")
            if ($closeParen -ge 0) {
                $fields = @($stat.Substring($closeParen + 1).Trim() -split "\s+")
                if ($fields.Count -gt 19 -and $fields[19] -match "^[0-9]+$") {
                    return "procfs-startticks:$($fields[19])"
                }
            }
        }
    }
    catch {
        return $null
    }
    finally {
        if ($null -ne $process) {
            $process.Dispose()
        }
    }
    return $null
}

function Test-BridgeInstallLockStale {
    param([Parameter(Mandatory = $true)][string] $LockDirectory)

    $ownerPath = Join-Path $LockDirectory "owner.json"
    $ageSeconds = ([DateTime]::UtcNow - [System.IO.Directory]::GetLastWriteTimeUtc($LockDirectory)).TotalSeconds
    if (-not (Test-Path -LiteralPath $ownerPath -PathType Leaf)) {
        return $ageSeconds -gt 1800
    }
    try {
        $owner = [System.IO.File]::ReadAllText($ownerPath) | ConvertFrom-Json
        if ($owner.created_unix -is [ValueType]) {
            $created = [DateTimeOffset]::FromUnixTimeSeconds([long]$owner.created_unix)
            $ageSeconds = ([DateTimeOffset]::UtcNow - $created).TotalSeconds
        }
        if ($owner.host -eq [Environment]::MachineName -and $owner.process_id -is [int]) {
            try {
                Get-Process -Id $owner.process_id -ErrorAction Stop | Out-Null
                $identityProperty = $owner.PSObject.Properties["process_start_identity"]
                $ownerIdentity = if ($null -ne $identityProperty) {
                    $identityProperty.Value
                }
                else {
                    $null
                }
                $currentIdentity = Get-ProcessStartIdentity -ProcessId $owner.process_id
                if ($ownerIdentity -is [string] -and
                    -not [string]::IsNullOrEmpty($ownerIdentity) -and
                    $currentIdentity -is [string] -and
                    -not [string]::IsNullOrEmpty($currentIdentity) -and
                    $ownerIdentity -cne $currentIdentity) {
                    return $true
                }
                # A same-host live owner remains authoritative regardless of
                # age. Slow filesystems and debugger pauses must not allow a
                # second installer to enter the replacement transaction.
                return $false
            }
            catch {
                return $true
            }
        }
    }
    catch {
        return $ageSeconds -gt 1800
    }
    return $ageSeconds -gt 1800
}

function Remove-StaleBridgeInstallLock {
    param([Parameter(Mandatory = $true)][string] $LockDirectory)

    $ownerPath = Join-Path $LockDirectory "owner.json"
    try {
        $observed = if (Test-Path -LiteralPath $ownerPath -PathType Leaf) {
            [System.IO.File]::ReadAllText($ownerPath)
        }
        else {
            $null
        }
        if ($null -ne $observed -and [System.IO.File]::ReadAllText($ownerPath) -cne $observed) {
            return $false
        }
        [System.IO.File]::Delete($ownerPath)
        [System.IO.Directory]::Delete($LockDirectory, $false)
        return $true
    }
    catch {
        return $false
    }
}

function Enter-BridgeInstallLock {
    param([Parameter(Mandatory = $true)][string] $LockDirectory)

    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    $token = "{0}-{1}" -f $PID, [Guid]::NewGuid().ToString("N")
    while ($true) {
        $created = $false
        $creationError = $null
        try {
            New-Item -ItemType Directory -Path $LockDirectory -ErrorAction Stop | Out-Null
            $created = $true
        }
        catch {
            $creationError = $_
        }
        if ($created) {
            try {
                $owner = @{
                    token = $token
                    process_id = $PID
                    process_start_identity = Get-ProcessStartIdentity -ProcessId $PID
                    host = [Environment]::MachineName
                    created_unix = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
                } | ConvertTo-Json -Compress
                [System.IO.File]::WriteAllText(
                    (Join-Path $LockDirectory "owner.json"),
                    $owner,
                    [System.Text.UTF8Encoding]::new($false)
                )
                return $token
            }
            catch {
                [System.IO.File]::Delete((Join-Path $LockDirectory "owner.json"))
                [System.IO.Directory]::Delete($LockDirectory, $false)
                throw
            }
        }
        if (-not (Test-Path -LiteralPath $LockDirectory -PathType Container)) {
            throw $creationError
        }
        if ((Test-BridgeInstallLockStale -LockDirectory $LockDirectory) -and
            (Remove-StaleBridgeInstallLock -LockDirectory $LockDirectory)) {
            continue
        }
        if ([DateTime]::UtcNow -ge $deadline) {
            throw "Timed out waiting for the Jak 3 bridge installation lock."
        }
        Start-Sleep -Milliseconds 25
    }
}

function Exit-BridgeInstallLock {
    param(
        [Parameter(Mandatory = $true)][string] $LockDirectory,
        [Parameter(Mandatory = $true)][string] $Token
    )

    $ownerPath = Join-Path $LockDirectory "owner.json"
    try {
        $owner = [System.IO.File]::ReadAllText($ownerPath) | ConvertFrom-Json
        if ($owner.token -ceq $Token) {
            [System.IO.File]::Delete($ownerPath)
            [System.IO.Directory]::Delete($LockDirectory, $false)
        }
    }
    catch {
        # Preserve the installation result; a later run can recover a stale lock.
    }
}

if (-not (Test-Path -LiteralPath $projectFile -PathType Leaf)) {
    throw "This does not look like an OpenGOAL Jak 3 repository: $projectFile was not found."
}
if (-not (Test-Path -LiteralPath $destinationDirectory -PathType Container)) {
    throw "The Jak 3 feature source directory was not found: $destinationDirectory"
}

$installLockToken = Enter-BridgeInstallLock -LockDirectory $installLockDirectory
try {
$manifest = Get-Content -LiteralPath $manifestSource -Raw | ConvertFrom-Json
Assert-ExactJsonFields $manifest `
    @("manifest_version", "source_set_format", "object_anchor", "modules") `
    "Bridge module manifest"
if (-not (Test-JsonIntegerScalar $manifest.manifest_version) -or
    $manifest.source_set_format -isnot [string] -or
    $manifest.object_anchor -isnot [string] -or
    $manifest.modules -isnot [System.Array]) {
    throw "Bridge module manifest fields have invalid JSON scalar types."
}
if ($manifest.manifest_version -ne 1 -or
    $manifest.source_set_format -ne "jak3-bridge-source-set-v1" -or
    $manifest.object_anchor -ne "task-control.o") {
    throw "Unsupported bridge module manifest contract."
}
$declaredModules = @($manifest.modules)
foreach ($module in $declaredModules) {
    Assert-ExactJsonFields $module `
        @("name", "order", "phase", "source", "resource", "destination", "object") `
        "Bridge module"
    if ($module.name -isnot [string] -or
        -not (Test-JsonIntegerScalar $module.order) -or
        $module.phase -isnot [string] -or $module.source -isnot [string] -or
        $module.resource -isnot [string] -or $module.destination -isnot [string] -or
        ($null -ne $module.object -and $module.object -isnot [string])) {
        throw "Bridge module fields have invalid JSON scalar types."
    }
}
$modules = @($manifest.modules | Sort-Object order)
$expectedNames = @("startup", "control", "diagnostics", "items")
$expectedOrders = @(10, 20, 30, 40)
$expectedPhases = @("pre_mi", "bridge", "bridge", "bridge")
$expectedSources = @(
    "goal_src/jak3/pc/features/archipelago-startup.gc",
    "goal_src/jak3/pc/features/archipelago.gc",
    "goal_src/jak3/pc/features/archipelago-diagnostics.gc",
    "goal_src/jak3/pc/features/archipelago-items.gc"
)
$expectedResources = @(
    "assets/opengoal/archipelago-startup.gc",
    "assets/opengoal/archipelago.gc",
    "assets/opengoal/archipelago-diagnostics.gc",
    "assets/opengoal/archipelago-items.gc"
)
$expectedObjects = @($null, "archipelago.o", "archipelago-diagnostics.o", "archipelago-items.o")
if ($modules.Count -ne 4) {
    throw "Bridge manifest must declare exactly four modules."
}
for ($index = 0; $index -lt $modules.Count; $index++) {
    $module = $modules[$index]
    Assert-ExactJsonFields $module `
        @("name", "order", "phase", "source", "resource", "destination", "object") `
        "Bridge module $index"
    if ($module.name -ne $expectedNames[$index] -or
        $module.order -ne $expectedOrders[$index] -or
        $module.phase -ne $expectedPhases[$index] -or
        $module.source -ne $expectedSources[$index] -or
        $module.resource -ne $expectedResources[$index] -or
        $module.destination -ne $expectedSources[$index] -or
        $module.object -ne $expectedObjects[$index]) {
        throw "Bridge modules are not in canonical version-1 order."
    }
    foreach ($field in @("source", "resource", "destination")) {
        $value = [string]$module.$field
        if ([string]::IsNullOrWhiteSpace($value) -or $value.Contains("\") -or
            [System.IO.Path]::IsPathRooted($value) -or $value.Split("/").Contains("..")) {
            throw "Unsafe bridge module $field path: $value"
        }
    }
    if ($module.source -ne $module.destination -or
        [System.IO.Path]::GetFileName($module.source) -ne [System.IO.Path]::GetFileName($module.resource)) {
        throw "Bridge module paths disagree for $($module.name)."
    }
}
foreach ($field in @("name", "order", "source", "resource", "destination", "object")) {
    $values = @($modules | ForEach-Object { $_.$field } | Where-Object { $null -ne $_ })
    if (@($values | Select-Object -Unique).Count -ne $values.Count) {
        throw "Bridge manifest contains duplicate $field values."
    }
}

$projectText = [System.IO.File]::ReadAllText($projectFile)
$markerPattern = '(?m)^([ \t]*"task-control\.o"[ \t]*)(?=\r?$)'
$markerMatches = [regex]::Matches($projectText, $markerPattern)
if ($markerMatches.Count -ne 1) {
    throw "Expected exactly one task-control.o entry in $projectFile; found $($markerMatches.Count)."
}
$runtimeObjects = @($modules | Where-Object { $null -ne $_.object } | ForEach-Object { $_.object })
foreach ($object in $runtimeObjects) {
    $objectPattern = "(?m)^[ \t]*`"$([regex]::Escape($object))`"[ \t]*(?=\r?$)"
    $objectMatches = [regex]::Matches($projectText, $objectPattern)
    if ($objectMatches.Count -gt 1) {
        throw "Expected at most one $object entry in $projectFile; found $($objectMatches.Count)."
    }
    if ($objectMatches.Count -eq 1 -and $objectMatches[0].Index -lt $markerMatches[0].Index) {
        throw "$object must load after task-control.o in $projectFile."
    }
}
$newline = if ($projectText.Contains("`r`n")) { "`r`n" } else { "`n" }
$indent = [regex]::Match($markerMatches[0].Value, '^[ \t]*').Value
$projectWithoutObjects = [regex]::Replace(
    $projectText,
    '(?m)^[ \t]*"(?:archipelago|archipelago-diagnostics|archipelago-items)\.o"[ \t]*\r?\n?',
    ''
)
$updatedMarker = [regex]::Match($projectWithoutObjects, $markerPattern)
$registration = ($runtimeObjects | ForEach-Object { "$indent`"$_`"" }) -join $newline
$updatedProjectText = $projectWithoutObjects.Insert(
    $updatedMarker.Index + $updatedMarker.Length,
    $newline + $registration
)
$projectUpdated = $updatedProjectText -ne $projectText
$projectText = $updatedProjectText

$manifestHash = Get-Sha256Hex -LiteralPath $manifestSource
$sourceSetText = "jak3-bridge-source-set-v1`nmanifest-sha256:$manifestHash`n"
$sourceUpdates = @()
foreach ($module in $modules) {
    $source = Join-Path $bridgeRoot $module.source.Replace("/", "\")
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Declared bridge source not found: $source"
    }
    $destination = Join-Path $repository $module.destination.Replace("/", "\")
    if ((Test-Path -LiteralPath $destination) -and
        -not (Test-Path -LiteralPath $destination -PathType Leaf)) {
        throw "Bridge destination is not a file: $destination"
    }
    $sourceHash = Get-Sha256Hex -LiteralPath $source
    $sourceSetText += "$($module.order):$($module.name):$sourceHash`n"
    if (-not (Test-Path -LiteralPath $destination -PathType Leaf) -or
        (Get-Sha256Hex -LiteralPath $destination) -ne $sourceHash) {
        $sourceUpdates += @{ source = $source; destination = $destination }
    }
}
$sourceSetHash = Get-Sha256Text -Text $sourceSetText
$manifestUpdated = -not (Test-Path -LiteralPath $manifestDestination -PathType Leaf) -or
    (Get-Sha256Hex -LiteralPath $manifestDestination) -ne $manifestHash
$replacementPaths = @($sourceUpdates | ForEach-Object { $_.destination })
if ($manifestUpdated) { $replacementPaths += $manifestDestination }
if ($projectUpdated) { $replacementPaths += $projectFile }
$originals = @{}
$missingOriginals = @{}
foreach ($path in $replacementPaths) {
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        $originals[$path] = [System.IO.File]::ReadAllBytes($path)
    }
    else {
        $missingOriginals[$path] = $true
    }
}
$stagingDirectory = Join-Path $destinationDirectory (".archipelago-install-" + [System.IO.Path]::GetRandomFileName())
$stagedFiles = @{}
try {
    New-Item -ItemType Directory -Path $stagingDirectory | Out-Null
    foreach ($module in $modules) {
        $source = Join-Path $bridgeRoot $module.source.Replace("/", "\")
        $destination = Join-Path $repository $module.destination.Replace("/", "\")
        $staged = Join-Path $stagingDirectory ([System.IO.Path]::GetRandomFileName())
        Copy-Item -LiteralPath $source -Destination $staged
        if ((Get-Sha256Hex -LiteralPath $staged) -ne (Get-Sha256Hex -LiteralPath $source)) {
            throw "Staged bridge source failed validation: $source"
        }
        $stagedFiles[$destination] = $staged
    }
    $stagedManifest = Join-Path $stagingDirectory ([System.IO.Path]::GetRandomFileName())
    Copy-Item -LiteralPath $manifestSource -Destination $stagedManifest
    if ((Get-Sha256Hex -LiteralPath $stagedManifest) -ne $manifestHash) {
        throw "Staged bridge manifest failed validation."
    }
    $stagedFiles[$manifestDestination] = $stagedManifest
    if ($projectUpdated) {
        $stagedProject = Join-Path $stagingDirectory ([System.IO.Path]::GetRandomFileName())
        [System.IO.File]::WriteAllText(
            $stagedProject,
            $projectText,
            [System.Text.UTF8Encoding]::new($false)
        )
        $stagedFiles[$projectFile] = $stagedProject
    }

    if ($sourceUpdates.Count -gt 0 -or $manifestUpdated) {
        # Persist the obligation only after the complete replacement set has
        # staged and validated, but before any installed file changes.
        [System.IO.File]::WriteAllText(
            $reloadMarker,
            $sourceSetHash + [Environment]::NewLine,
            [System.Text.UTF8Encoding]::new($false)
        )
    }
    foreach ($update in $sourceUpdates) {
        $staged = $stagedFiles[$update.destination]
        if (Test-Path -LiteralPath $update.destination -PathType Leaf) {
            $replacementBackup = Join-Path $stagingDirectory ([System.IO.Path]::GetRandomFileName())
            [System.IO.File]::Replace($staged, $update.destination, $replacementBackup, $true)
            Remove-Item -LiteralPath $replacementBackup -Force
        }
        else {
            Move-Item -LiteralPath $staged -Destination $update.destination
        }
    }
    if ($manifestUpdated) {
        $staged = $stagedFiles[$manifestDestination]
        if (Test-Path -LiteralPath $manifestDestination -PathType Leaf) {
            $replacementBackup = Join-Path $stagingDirectory ([System.IO.Path]::GetRandomFileName())
            [System.IO.File]::Replace($staged, $manifestDestination, $replacementBackup, $true)
            Remove-Item -LiteralPath $replacementBackup -Force
        }
        else {
            Move-Item -LiteralPath $staged -Destination $manifestDestination
        }
    }
    if ($projectUpdated) {
        $replacementBackup = Join-Path $stagingDirectory ([System.IO.Path]::GetRandomFileName())
        [System.IO.File]::Replace(
            $stagedFiles[$projectFile], $projectFile, $replacementBackup, $true
        )
        Remove-Item -LiteralPath $replacementBackup -Force
    }
}
catch {
    foreach ($path in $replacementPaths) {
        try {
            if ($missingOriginals.ContainsKey($path)) {
                Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
            }
            else {
                [System.IO.File]::WriteAllBytes($path, $originals[$path])
            }
        }
        catch {
            # Keep the reload marker and preserve the original failure.
        }
    }
    throw
}
finally {
    Remove-Item -LiteralPath $stagingDirectory -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Installed Jak 3 Archipelago bridge source set: $sourceSetHash"
Write-Host "Registered control, diagnostics, and items bridge objects after task-control.o in: $projectFile"
Write-Host "Bridge installation complete."
Write-Host "Launching Jak 3 Client now starts Debug gk/goalc, recompiles, and verifies protocol 3."
}
finally {
    Exit-BridgeInstallLock -LockDirectory $installLockDirectory -Token $installLockToken
}
