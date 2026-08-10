[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        "Annotate",
        "Capture",
        "Evidence",
        "NreplAttach",
        "NreplCompile",
        "NreplBridgeLoad",
        "ProfilerFrames",
        "Query",
        "SetTestTarget",
        "Sample",
        "Analyze"
    )]
    [string] $Action,

    [Parameter(Mandatory = $true)]
    [string] $OutputDirectory,

    [string] $SnapshotPath,
    [string] $Label = "unlabeled",
    [string] $Note,
    [string[]] $EvidencePaths = @(),
    [int[]] $ProcessIds = @(),
    [string[]] $SamplePaths = @(),
    [ValidateRange(1, 86400)]
    [int] $DurationSeconds = 1,
    [ValidateRange(1, 60)]
    [int] $IntervalSeconds = 1,
    [ValidateRange(0, 2147483647)]
    [int] $CommandId = 0,
    [ValidateSet(0, 1)]
    [int] $Target = 1,
    [string] $MetricsPath,
    [string] $FrameMetricsPath,
    [string] $ProfilerTracePath,
    [string] $ControlLabel = "control",
    [string] $ConnectedLabel = "connected",
    [string] $OpenGoalProject
)

$ErrorActionPreference = "Stop"
$scriptVersion = 1
$utf8 = [System.Text.UTF8Encoding]::new($false)
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $resolvedOutput -Force | Out-Null
$recordPath = Join-Path $resolvedOutput "recorder.jsonl"
$defaultMetricsPath = Join-Path $resolvedOutput "metrics.jsonl"

function Get-UtcTimestamp {
    [DateTime]::UtcNow.ToString("o", [Globalization.CultureInfo]::InvariantCulture)
}

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string] $Path)

    $stream = [System.IO.File]::OpenRead($Path)
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        ([BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $algorithm.Dispose()
        $stream.Dispose()
    }
}

function Get-TextSha256 {
    param([AllowEmptyString()][string] $Value)

    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = $utf8.GetBytes($Value)
        ([BitConverter]::ToString($algorithm.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $algorithm.Dispose()
    }
}

function Add-JsonLine {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][object] $Value
    )

    $line = $Value | ConvertTo-Json -Depth 12 -Compress
    [System.IO.File]::AppendAllText($Path, $line + [Environment]::NewLine, $utf8)
}

function New-Record {
    param(
        [Parameter(Mandatory = $true)][string] $Kind,
        [Parameter(Mandatory = $true)][object] $Data
    )

    [ordered]@{
        schema_version = $scriptVersion
        timestamp_utc = Get-UtcTimestamp
        kind = $Kind
        label = $Label
        data = $Data
    }
}

function Read-SnapshotFields {
    param([Parameter(Mandatory = $true)][string] $Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Bridge snapshot not found: $Path"
    }
    $fields = @{}
    $lines = [System.IO.File]::ReadAllLines($Path, $utf8)
    if ($lines.Count -lt 2 -or -not $lines[0].StartsWith("snapshot_begin ") -or
        -not $lines[$lines.Count - 1].StartsWith("snapshot_end ")) {
        throw "Bridge snapshot is incomplete: $Path"
    }
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        $parts = $line.Split(@(" "), 2, [StringSplitOptions]::None)
        if ($parts.Count -eq 2) {
            $fields[$parts[0]] = $parts[1]
        }
    }
    if ($fields["snapshot_begin"] -ne $fields["snapshot_end"]) {
        throw "Bridge snapshot revisions do not match: $Path"
    }
    $required = @(
        "protocol_version", "game_integration_version", "state_schema_version",
        "slot_data_version", "item_table_version", "location_table_version",
        "mission_table_version", "item_table_hash", "location_table_hash",
        "mission_table_hash", "client_session_id", "session_nonce", "client_status",
        "client_heartbeat", "game_heartbeat", "save_loaded", "native_save_slot",
        "native_save_identity", "native_save_eligibility", "ap_state_loaded",
        "ap_state_bound", "at_title_menu", "safe_to_mutate_mission_state",
        "test_target", "last_command_id", "last_command_result", "last_error_code"
    )
    foreach ($key in $required) {
        if (-not $fields.ContainsKey($key)) {
            throw "Bridge snapshot is missing required field: $key"
        }
    }
    $fields
}

function ConvertTo-OptionalHash {
    param([string] $Value)

    if ([string]::IsNullOrWhiteSpace($Value) -or $Value -eq "-") {
        return $null
    }
    (Get-TextSha256 $Value).Substring(0, 16)
}

function Get-SanitizedSnapshot {
    param([Parameter(Mandatory = $true)][hashtable] $Fields)

    [ordered]@{
        snapshot_revision = [int64]$Fields["snapshot_begin"]
        protocol_version = [int]$Fields["protocol_version"]
        game_integration_version = [int]$Fields["game_integration_version"]
        bridge_runtime_version = if ($Fields.ContainsKey("bridge_runtime_version")) { [int]$Fields["bridge_runtime_version"] } else { $null }
        bridge_activation_generation = if ($Fields.ContainsKey("bridge_activation_generation")) { [int]$Fields["bridge_activation_generation"] } else { $null }
        client_session_hash = ConvertTo-OptionalHash $Fields["client_session_id"]
        game_nonce_hash = ConvertTo-OptionalHash $Fields["session_nonce"]
        client_status = [int]$Fields["client_status"]
        client_heartbeat = [int64]$Fields["client_heartbeat"]
        game_heartbeat = [int64]$Fields["game_heartbeat"]
        save_loaded = [int]$Fields["save_loaded"]
        native_save_slot = [int]$Fields["native_save_slot"]
        native_save_identity_hash = ConvertTo-OptionalHash $Fields["native_save_identity"]
        native_save_eligibility = [int]$Fields["native_save_eligibility"]
        ap_state_loaded = [int]$Fields["ap_state_loaded"]
        ap_state_bound = [int]$Fields["ap_state_bound"]
        at_title_menu = [int]$Fields["at_title_menu"]
        safe_to_mutate_mission_state = [int]$Fields["safe_to_mutate_mission_state"]
        test_target = [int]$Fields["test_target"]
        last_command_id = [int64]$Fields["last_command_id"]
        last_command_result = [int]$Fields["last_command_result"]
        last_error_code = [int]$Fields["last_error_code"]
        recent_command_count = if ($Fields.ContainsKey("recent_command_count")) { [int]$Fields["recent_command_count"] } else { $null }
        diagnostic_next_sequence = if ($Fields.ContainsKey("diagnostic_next_sequence")) { [int64]$Fields["diagnostic_next_sequence"] } else { $null }
    }
}

function Assert-WireToken {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][string] $Value,
        [switch] $AllowMissing
    )

    if ($AllowMissing -and $Value -eq "-") {
        return
    }
    if ($Value -notmatch '^[A-Za-z0-9._:-]+$') {
        throw "$Name contains characters that cannot be emitted by this restricted recorder."
    }
}

function Invoke-NreplForm {
    param(
        [Parameter(Mandatory = $true)][string] $Form,
        [ValidateRange(1, 900)][int] $TimeoutSeconds = 60
    )

    $client = [System.Net.Sockets.TcpClient]::new()
    $timer = [Diagnostics.Stopwatch]::StartNew()
    try {
        $connect = $client.BeginConnect("127.0.0.1", 8181, $null, $null)
        if (-not $connect.AsyncWaitHandle.WaitOne([TimeSpan]::FromSeconds(10))) {
            throw "Timed out connecting to OpenGOAL nREPL."
        }
        $client.EndConnect($connect)
        $stream = $client.GetStream()
        $stream.ReadTimeout = 10000
        $greetingBuffer = [byte[]]::new(4096)
        $greetingCount = $stream.Read($greetingBuffer, 0, $greetingBuffer.Length)
        $greeting = $utf8.GetString($greetingBuffer, 0, $greetingCount)
        if ($greeting -notmatch "nREPL") {
            throw "Unexpected OpenGOAL nREPL greeting."
        }
        $encoded = $utf8.GetBytes($Form)
        $packet = [System.IO.MemoryStream]::new()
        try {
            $lengthBytes = [BitConverter]::GetBytes([uint32]$encoded.Length)
            $kindBytes = [BitConverter]::GetBytes([uint32]10)
            $pingBytes = [byte[]]::new(8)
            $packet.Write($lengthBytes, 0, $lengthBytes.Length)
            $packet.Write($kindBytes, 0, $kindBytes.Length)
            $packet.Write($encoded, 0, $encoded.Length)
            $packet.Write($pingBytes, 0, $pingBytes.Length)
            $payload = $packet.ToArray()
        }
        finally {
            $packet.Dispose()
        }
        $stream.WriteTimeout = $TimeoutSeconds * 1000
        $stream.ReadTimeout = $TimeoutSeconds * 1000
        $stream.Write($payload, 0, $payload.Length)
        $stream.Flush()
        $responseBuffer = [byte[]]::new(16384)
        $responseCount = $stream.Read($responseBuffer, 0, $responseBuffer.Length)
        $response = $utf8.GetString($responseBuffer, 0, $responseCount)
        if ($response -notmatch "nREPL") {
            throw "OpenGOAL did not return the nREPL completion barrier."
        }
        $timer.Stop()
        [ordered]@{
            elapsed_ms = [Math]::Round($timer.Elapsed.TotalMilliseconds, 3)
            form_sha256 = Get-TextSha256 $Form
            response_bytes = $responseCount
        }
    }
    finally {
        $timer.Stop()
        $client.Dispose()
    }
}

function Invoke-RestrictedForm {
    param(
        [Parameter(Mandatory = $true)][string] $Operation,
        [Parameter(Mandatory = $true)][string] $Form,
        [ValidateRange(1, 900)][int] $TimeoutSeconds = 60
    )

    $result = Invoke-NreplForm -Form $Form -TimeoutSeconds $TimeoutSeconds
    $data = [ordered]@{
        operation = $Operation
        elapsed_ms = $result.elapsed_ms
        form_sha256 = $result.form_sha256
        response_bytes = $result.response_bytes
    }
    Add-JsonLine $recordPath (New-Record "nrepl.timing" $data)
    $data
}

function Get-CommandForm {
    param(
        [Parameter(Mandatory = $true)][hashtable] $Fields,
        [Parameter(Mandatory = $true)][int] $SelectedCommandId,
        [Parameter(Mandatory = $true)][int] $SelectedTarget
    )

    $clientSession = [string]$Fields["client_session_id"]
    $gameSession = [string]$Fields["session_nonce"]
    $saveIdentity = [string]$Fields["native_save_identity"]
    Assert-WireToken "client_session_id" $clientSession
    Assert-WireToken "session_nonce" $gameSession
    Assert-WireToken "native_save_identity" $saveIdentity -AllowMissing
    foreach ($hashField in @("item_table_hash", "location_table_hash", "mission_table_hash")) {
        Assert-WireToken $hashField ([string]$Fields[$hashField])
    }
    $stateFlags = ([int]$Fields["ap_state_loaded"]) + (2 * [int]$Fields["ap_state_bound"])
    $slot = if ($stateFlags -eq 3) { [int]$Fields["native_save_slot"] } else { -1 }
    if ($stateFlags -ne 3) {
        $saveIdentity = "-"
    }
    '(ap-command! "{0}" "{1}" {2} 100 {3} {4} {5} "{6}" {7} {8} {9} {10} {11} {12} {13} "{14}" "{15}" "{16}")' -f @(
        $clientSession,
        $gameSession,
        $SelectedCommandId,
        $SelectedTarget,
        $stateFlags,
        $slot,
        $saveIdentity,
        [int]$Fields["protocol_version"],
        [int]$Fields["game_integration_version"],
        [int]$Fields["state_schema_version"],
        [int]$Fields["slot_data_version"],
        [int]$Fields["item_table_version"],
        [int]$Fields["location_table_version"],
        [int]$Fields["mission_table_version"],
        $Fields["item_table_hash"],
        $Fields["location_table_hash"],
        $Fields["mission_table_hash"]
    )
}

function Get-QueryForm {
    param([Parameter(Mandatory = $true)][hashtable] $Fields)

    $clientSession = [string]$Fields["client_session_id"]
    $gameSession = [string]$Fields["session_nonce"]
    $saveIdentity = [string]$Fields["native_save_identity"]
    Assert-WireToken "client_session_id" $clientSession
    Assert-WireToken "session_nonce" $gameSession
    Assert-WireToken "native_save_identity" $saveIdentity -AllowMissing
    $stateFlags = ([int]$Fields["ap_state_loaded"]) + (2 * [int]$Fields["ap_state_bound"])
    $slot = if ($stateFlags -eq 3) { [int]$Fields["native_save_slot"] } else { -1 }
    if ($stateFlags -ne 3) {
        $saveIdentity = "-"
    }
    '(ap-query-state! "{0}" "{1}" {2} {3} {4} "{5}")' -f @(
        $clientSession, $gameSession, [int]$Fields["client_status"],
        $stateFlags, $slot, $saveIdentity
    )
}

function Get-Percentile {
    param(
        [Parameter(Mandatory = $true)][double[]] $Values,
        [Parameter(Mandatory = $true)][double] $Percentile
    )

    if ($Values.Count -eq 0) {
        return $null
    }
    $ordered = @($Values | Sort-Object)
    $index = [Math]::Ceiling(($Percentile / 100.0) * $ordered.Count) - 1
    $ordered[[Math]::Max(0, [Math]::Min($ordered.Count - 1, $index))]
}

function Read-JsonLines {
    param([Parameter(Mandatory = $true)][string] $Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Metric fixture not found: $Path"
    }
    @(
        [System.IO.File]::ReadAllLines($Path, $utf8) |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
            ForEach-Object { $_ | ConvertFrom-Json }
    )
}

switch ($Action) {
    "Annotate" {
        if ([string]::IsNullOrWhiteSpace($Note)) {
            throw "Annotate requires -Note."
        }
        Add-JsonLine $recordPath (New-Record "operator.annotation" ([ordered]@{ note = $Note }))
        Write-Output $recordPath
    }

    "Capture" {
        if ([string]::IsNullOrWhiteSpace($SnapshotPath)) {
            throw "Capture requires -SnapshotPath."
        }
        $resolvedSnapshot = (Resolve-Path -LiteralPath $SnapshotPath).Path
        $fields = Read-SnapshotFields $resolvedSnapshot
        $data = [ordered]@{
            snapshot_sha256 = Get-Sha256 $resolvedSnapshot
            snapshot = Get-SanitizedSnapshot $fields
        }
        Add-JsonLine $recordPath (New-Record "snapshot.capture" $data)
        $data | ConvertTo-Json -Depth 8
    }

    "Evidence" {
        if ($EvidencePaths.Count -eq 0) {
            throw "Evidence requires at least one -EvidencePaths value."
        }
        $items = @()
        foreach ($path in $EvidencePaths) {
            $resolved = (Resolve-Path -LiteralPath $path).Path
            $item = Get-Item -LiteralPath $resolved
            if ($item.PSIsContainer) {
                throw "Evidence paths must be files: $resolved"
            }
            $items += [ordered]@{
                name = $item.Name
                length = [int64]$item.Length
                sha256 = Get-Sha256 $resolved
            }
        }
        $data = [ordered]@{ files = $items }
        Add-JsonLine $recordPath (New-Record "evidence.hashes" $data)
        $data | ConvertTo-Json -Depth 8
    }

    "NreplAttach" {
        Invoke-RestrictedForm "attach" "(lt)" 30 | ConvertTo-Json
    }

    "NreplCompile" {
        Invoke-RestrictedForm "full_compile" "(mi)" 900 | ConvertTo-Json
    }

    "NreplBridgeLoad" {
        if ([string]::IsNullOrWhiteSpace($OpenGoalProject)) {
            throw "NreplBridgeLoad requires -OpenGoalProject."
        }
        $manifestPath = Join-Path $OpenGoalProject "goal_src\jak3\pc\features\archipelago-bridge-modules.json"
        if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
            throw "Installed bridge manifest not found: $manifestPath"
        }
        $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
        $modules = @($manifest.modules | Sort-Object order)
        $allowed = @(
            "goal_src/jak3/pc/features/archipelago-startup.gc",
            "goal_src/jak3/pc/features/archipelago.gc",
            "goal_src/jak3/pc/features/archipelago-diagnostics.gc"
        )
        if ($modules.Count -ne 3 -or (@($modules | ForEach-Object { $_.destination }) -join "|") -ne ($allowed -join "|")) {
            throw "Installed bridge manifest is not the frozen version 1 module order."
        }
        $results = @()
        $total = [Diagnostics.Stopwatch]::StartNew()
        foreach ($source in $allowed) {
            $results += Invoke-RestrictedForm ("module_load:" + [IO.Path]::GetFileName($source)) ('(ml "{0}")' -f $source) 120
        }
        $total.Stop()
        $data = [ordered]@{
            operation = "manifest_ordered_bridge_load"
            elapsed_ms = [Math]::Round($total.Elapsed.TotalMilliseconds, 3)
            modules = $results
        }
        Add-JsonLine $recordPath (New-Record "nrepl.bridge_load_total" $data)
        $data | ConvertTo-Json -Depth 8
    }

    "Query" {
        if ([string]::IsNullOrWhiteSpace($SnapshotPath)) {
            throw "Query requires -SnapshotPath."
        }
        $fields = Read-SnapshotFields $SnapshotPath
        $beforeHash = Get-Sha256 $SnapshotPath
        $timing = Invoke-RestrictedForm "query_state" (Get-QueryForm $fields) 30
        Start-Sleep -Milliseconds 100
        $afterFields = Read-SnapshotFields $SnapshotPath
        $data = [ordered]@{
            timing = $timing
            before_snapshot_sha256 = $beforeHash
            after_snapshot_sha256 = Get-Sha256 $SnapshotPath
            after = Get-SanitizedSnapshot $afterFields
        }
        Add-JsonLine $recordPath (New-Record "protocol.query_probe" $data)
        $data | ConvertTo-Json -Depth 10
    }

    "ProfilerFrames" {
        if ([string]::IsNullOrWhiteSpace($ProfilerTracePath)) {
            throw "ProfilerFrames requires -ProfilerTracePath."
        }
        $resolvedTrace = (Resolve-Path -LiteralPath $ProfilerTracePath).Path
        $profile = [System.IO.File]::ReadAllText($resolvedTrace, $utf8) | ConvertFrom-Json
        $events = @($profile.traceEvents)
        if ($events.Count -eq 0) {
            throw "OpenGOAL profiler trace contains no events: $resolvedTrace"
        }
        $graphicsThread = @(
            $events |
                Where-Object { $_.ph -eq "B" -and $_.name -eq "drawing" } |
                Group-Object tid |
                Sort-Object Count -Descending |
                Select-Object -First 1
        )
        if ($graphicsThread.Count -ne 1) {
            throw "OpenGOAL profiler trace has no graphics drawing events: $resolvedTrace"
        }
        $graphicsThreadId = [int]$graphicsThread[0].Name
        $roots = @(
            $events |
                Where-Object {
                    [int]$_.tid -eq $graphicsThreadId -and $_.ph -eq "i" -and
                    $_.name -eq "ROOT"
                } |
                Sort-Object { [double]$_.ts }
        )
        if ($roots.Count -lt 2) {
            throw "OpenGOAL profiler trace has fewer than two graphics frame roots: $resolvedTrace"
        }
        $durations = @()
        for ($index = 1; $index -lt $roots.Count; $index++) {
            # Chrome trace timestamps are microseconds. OpenGOAL emits a graphics ROOT
            # marker once per rendered frame, so adjacent roots delimit frame time.
            $duration = ([double]$roots[$index].ts - [double]$roots[$index - 1].ts) / 1000.0
            if ($duration -gt 0) {
                $durations += $duration
            }
        }
        if ($durations.Count -eq 0) {
            throw "OpenGOAL profiler trace has no positive graphics frame durations: $resolvedTrace"
        }
        $destination = if ([string]::IsNullOrWhiteSpace($MetricsPath)) {
            Join-Path $resolvedOutput "frame-metrics.jsonl"
        }
        else {
            [IO.Path]::GetFullPath($MetricsPath)
        }
        $traceHash = Get-Sha256 $resolvedTrace
        foreach ($duration in $durations) {
            Add-JsonLine $destination ([ordered]@{
                schema_version = $scriptVersion
                kind = "frame.sample"
                label = $Label
                duration_ms = [Math]::Round($duration, 6)
                trace_sha256 = $traceHash
            })
        }
        $data = [ordered]@{
            trace_sha256 = $traceHash
            graphics_thread_id = $graphicsThreadId
            samples = $durations.Count
            p50_ms = [Math]::Round((Get-Percentile $durations 50), 4)
            p95_ms = [Math]::Round((Get-Percentile $durations 95), 4)
            p99_ms = [Math]::Round((Get-Percentile $durations 99), 4)
            metrics_path = $destination
        }
        Add-JsonLine $recordPath (New-Record "profiler.frames" $data)
        $data | ConvertTo-Json -Depth 6
    }

    "SetTestTarget" {
        if ([string]::IsNullOrWhiteSpace($SnapshotPath)) {
            throw "SetTestTarget requires -SnapshotPath."
        }
        $fields = Read-SnapshotFields $SnapshotPath
        $beforeHash = Get-Sha256 $SnapshotPath
        $form = Get-CommandForm $fields $CommandId $Target
        $timing = Invoke-RestrictedForm "set_test_target" $form 30
        $acknowledged = $false
        $ackDeadline = [DateTime]::UtcNow.AddSeconds(2)
        do {
            Start-Sleep -Milliseconds 100
            $afterFields = Read-SnapshotFields $SnapshotPath
            $acknowledged = [int64]$afterFields["last_command_id"] -eq $CommandId
            if (-not $acknowledged) {
                $receiptCount = [int]$afterFields["recent_command_count"]
                for ($index = 0; $index -lt $receiptCount; $index++) {
                    $receiptIdKey = "recent_command_${index}_id"
                    if ($afterFields.ContainsKey($receiptIdKey) -and
                        [int64]$afterFields[$receiptIdKey] -eq $CommandId) {
                        $acknowledged = $true
                        break
                    }
                }
            }
        } while (-not $acknowledged -and [DateTime]::UtcNow -lt $ackDeadline)
        if (-not $acknowledged) {
            throw "OpenGOAL snapshot did not acknowledge command ID $CommandId."
        }
        $data = [ordered]@{
            command_id = $CommandId
            target = $Target
            timing = $timing
            before_snapshot_sha256 = $beforeHash
            after_snapshot_sha256 = Get-Sha256 $SnapshotPath
            after = Get-SanitizedSnapshot $afterFields
        }
        Add-JsonLine $recordPath (New-Record "protocol.command_probe" $data)
        $data | ConvertTo-Json -Depth 10
    }

    "Sample" {
        if ($ProcessIds.Count -eq 0 -and $SamplePaths.Count -eq 0 -and [string]::IsNullOrWhiteSpace($SnapshotPath)) {
            throw "Sample requires process IDs, file paths, or a snapshot path."
        }
        $destination = if ([string]::IsNullOrWhiteSpace($MetricsPath)) { $defaultMetricsPath } else { [IO.Path]::GetFullPath($MetricsPath) }
        $logicalProcessors = [Environment]::ProcessorCount
        $deadline = [DateTime]::UtcNow.AddSeconds($DurationSeconds)
        do {
            $processes = @()
            foreach ($id in $ProcessIds) {
                $process = Get-Process -Id $id -ErrorAction SilentlyContinue
                if ($null -eq $process) {
                    $processes += [ordered]@{ process_id = $id; exited = $true }
                }
                else {
                    $processes += [ordered]@{
                        process_id = $id
                        name = $process.ProcessName
                        start_time_utc = $process.StartTime.ToUniversalTime().ToString("o")
                        processor_seconds = [Math]::Round($process.TotalProcessorTime.TotalSeconds, 6)
                        private_bytes = [int64]$process.PrivateMemorySize64
                        working_set_bytes = [int64]$process.WorkingSet64
                        exited = $false
                    }
                }
            }
            $files = @()
            foreach ($path in $SamplePaths) {
                $item = Get-Item -LiteralPath $path -ErrorAction SilentlyContinue
                if ($null -eq $item) {
                    $files += [ordered]@{ path = [IO.Path]::GetFullPath($path); exists = $false }
                }
                elseif ($item.PSIsContainer) {
                    throw "Sample paths must be files: $path"
                }
                else {
                    $files += [ordered]@{
                        path = $item.FullName
                        exists = $true
                        length = [int64]$item.Length
                        last_write_time_utc = $item.LastWriteTimeUtc.ToString("o")
                    }
                }
            }
            $snapshot = $null
            if (-not [string]::IsNullOrWhiteSpace($SnapshotPath) -and (Test-Path -LiteralPath $SnapshotPath -PathType Leaf)) {
                try {
                    $snapshotFields = Read-SnapshotFields $SnapshotPath
                    $snapshotItem = Get-Item -LiteralPath $SnapshotPath
                    $snapshot = [ordered]@{
                        revision = [int64]$snapshotFields["snapshot_begin"]
                        client_heartbeat = [int64]$snapshotFields["client_heartbeat"]
                        game_heartbeat = [int64]$snapshotFields["game_heartbeat"]
                        length = [int64]$snapshotItem.Length
                        last_write_time_utc = $snapshotItem.LastWriteTimeUtc.ToString("o")
                    }
                }
                catch {
                    $snapshot = [ordered]@{ incomplete = $true }
                }
            }
            $sample = [ordered]@{
                schema_version = $scriptVersion
                timestamp_utc = Get-UtcTimestamp
                kind = "runtime.sample"
                label = $Label
                logical_processors = $logicalProcessors
                processes = $processes
                files = $files
                snapshot = $snapshot
            }
            Add-JsonLine $destination $sample
            if ([DateTime]::UtcNow -lt $deadline) {
                Start-Sleep -Seconds $IntervalSeconds
            }
        } while ([DateTime]::UtcNow -lt $deadline)
        Write-Output $destination
    }

    "Analyze" {
        $source = if ([string]::IsNullOrWhiteSpace($MetricsPath)) { $defaultMetricsPath } else { [IO.Path]::GetFullPath($MetricsPath) }
        $samples = @(Read-JsonLines $source | Where-Object { $_.kind -eq "runtime.sample" })
        if ($samples.Count -lt 2) {
            throw "Analyze requires at least two runtime samples."
        }
        $groupResults = @()
        foreach ($group in @($samples | Group-Object label)) {
            $orderedSamples = @($group.Group | Sort-Object { [DateTime]$_.timestamp_utc })
            $cpuValues = @()
            for ($index = 1; $index -lt $orderedSamples.Count; $index++) {
                $before = $orderedSamples[$index - 1]
                $after = $orderedSamples[$index]
                $elapsed = ([DateTime]$after.timestamp_utc - [DateTime]$before.timestamp_utc).TotalSeconds
                if ($elapsed -le 0) { continue }
                $totalDelta = 0.0
                foreach ($afterProcess in @($after.processes | Where-Object { -not $_.exited })) {
                    $beforeProcess = $before.processes | Where-Object { $_.process_id -eq $afterProcess.process_id -and -not $_.exited } | Select-Object -First 1
                    if ($null -ne $beforeProcess) {
                        $delta = [double]$afterProcess.processor_seconds - [double]$beforeProcess.processor_seconds
                        if ($delta -ge 0) { $totalDelta += $delta }
                    }
                }
                $cpuValues += 100.0 * $totalDelta / ($elapsed * [int]$after.logical_processors)
            }
            $first = $orderedSamples[0]
            $last = $orderedSamples[$orderedSamples.Count - 1]
            $durationHours = ([DateTime]$last.timestamp_utc - [DateTime]$first.timestamp_utc).TotalHours
            $firstPrivate = [double](($first.processes | Where-Object { -not $_.exited } | Measure-Object private_bytes -Sum).Sum)
            $lastPrivate = [double](($last.processes | Where-Object { -not $_.exited } | Measure-Object private_bytes -Sum).Sum)
            $snapshotWrites = 0
            $snapshotBytes = 0.0
            for ($index = 1; $index -lt $orderedSamples.Count; $index++) {
                $beforeSnapshot = $orderedSamples[$index - 1].snapshot
                $afterSnapshot = $orderedSamples[$index].snapshot
                if ($null -ne $beforeSnapshot -and $null -ne $afterSnapshot -and
                    $null -ne $afterSnapshot.last_write_time_utc -and
                    $afterSnapshot.last_write_time_utc -ne $beforeSnapshot.last_write_time_utc) {
                    $snapshotWrites++
                    $snapshotBytes += [double]$afterSnapshot.length
                }
            }
            $elapsedSeconds = $durationHours * 3600.0
            $firstSnapshot = $first.snapshot
            $lastSnapshot = $last.snapshot
            $clientHeartbeatHz = $null
            $gameHeartbeatHz = $null
            if ($elapsedSeconds -gt 0 -and $null -ne $firstSnapshot -and $null -ne $lastSnapshot -and
                $null -ne $firstSnapshot.client_heartbeat -and $null -ne $lastSnapshot.client_heartbeat) {
                $clientHeartbeatHz = ([double]$lastSnapshot.client_heartbeat - [double]$firstSnapshot.client_heartbeat) / $elapsedSeconds
                $gameHeartbeatHz = ([double]$lastSnapshot.game_heartbeat - [double]$firstSnapshot.game_heartbeat) / $elapsedSeconds
            }
            $fileResults = @()
            $filePaths = @(
                $orderedSamples |
                    ForEach-Object { @($_.files) } |
                    ForEach-Object { $_.path } |
                    Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
                    Sort-Object -Unique
            )
            foreach ($path in $filePaths) {
                $positiveGrowth = 0.0
                $maximumLength = 0.0
                for ($index = 0; $index -lt $orderedSamples.Count; $index++) {
                    $current = $orderedSamples[$index].files | Where-Object { $_.path -eq $path -and $_.exists } | Select-Object -First 1
                    if ($null -ne $current) {
                        $maximumLength = [Math]::Max($maximumLength, [double]$current.length)
                    }
                    if ($index -eq 0) { continue }
                    $previous = $orderedSamples[$index - 1].files | Where-Object { $_.path -eq $path -and $_.exists } | Select-Object -First 1
                    if ($null -ne $previous -and $null -ne $current) {
                        $delta = [double]$current.length - [double]$previous.length
                        if ($delta -gt 0) { $positiveGrowth += $delta }
                    }
                }
                $fileResults += [ordered]@{
                    name = [IO.Path]::GetFileName($path)
                    path_hash = (Get-TextSha256 $path).Substring(0, 16)
                    maximum_bytes = [int64]$maximumLength
                    positive_growth_bytes_per_hour = if ($durationHours -gt 0) { [Math]::Round($positiveGrowth / $durationHours, 3) } else { $null }
                }
            }
            $groupResults += [ordered]@{
                label = $group.Name
                samples = $orderedSamples.Count
                duration_seconds = [Math]::Round($elapsedSeconds, 3)
                normalized_cpu_p50_pct = if ($cpuValues.Count) { [Math]::Round((Get-Percentile $cpuValues 50), 4) } else { $null }
                normalized_cpu_p95_pct = if ($cpuValues.Count) { [Math]::Round((Get-Percentile $cpuValues 95), 4) } else { $null }
                private_memory_start_bytes = [int64]$firstPrivate
                private_memory_end_bytes = [int64]$lastPrivate
                private_memory_growth_bytes = [int64]($lastPrivate - $firstPrivate)
                client_heartbeat_hz = if ($null -ne $clientHeartbeatHz) { [Math]::Round($clientHeartbeatHz, 4) } else { $null }
                game_heartbeat_hz = if ($null -ne $gameHeartbeatHz) { [Math]::Round($gameHeartbeatHz, 4) } else { $null }
                snapshot_writes_per_hour = if ($durationHours -gt 0) { [Math]::Round($snapshotWrites / $durationHours, 3) } else { $null }
                snapshot_bytes_per_hour = if ($durationHours -gt 0) { [Math]::Round($snapshotBytes / $durationHours, 3) } else { $null }
                files = $fileResults
            }
        }
        $frames = @()
        if (-not [string]::IsNullOrWhiteSpace($FrameMetricsPath)) {
            $frames = @(Read-JsonLines ([IO.Path]::GetFullPath($FrameMetricsPath)) | Where-Object { $_.kind -eq "frame.sample" })
        }
        $frameResults = @()
        foreach ($group in @($frames | Group-Object label)) {
            $values = [double[]]@($group.Group | ForEach-Object { [double]$_.duration_ms })
            $frameResults += [ordered]@{
                label = $group.Name
                samples = $values.Count
                p50_ms = [Math]::Round((Get-Percentile $values 50), 4)
                p95_ms = [Math]::Round((Get-Percentile $values 95), 4)
                p99_ms = [Math]::Round((Get-Percentile $values 99), 4)
            }
        }
        $control = $groupResults | Where-Object { $_.label -eq $ControlLabel } | Select-Object -First 1
        $connected = $groupResults | Where-Object { $_.label -eq $ConnectedLabel } | Select-Object -First 1
        $controlFrame = $frameResults | Where-Object { $_.label -eq $ControlLabel } | Select-Object -First 1
        $connectedFrame = $frameResults | Where-Object { $_.label -eq $ConnectedLabel } | Select-Object -First 1
        $cpuRegression = if ($null -ne $control -and $null -ne $connected) { [double]$connected.normalized_cpu_p95_pct - [double]$control.normalized_cpu_p95_pct } else { $null }
        $frameRegression = if ($null -ne $controlFrame -and $null -ne $connectedFrame) { [double]$connectedFrame.p95_ms - [double]$controlFrame.p95_ms } else { $null }
        $memoryGrowth = if ($null -ne $connected) { [int64]$connected.private_memory_growth_bytes } else { $null }
        $clientHeartbeat = if ($null -ne $connected) { $connected.client_heartbeat_hz } else { $null }
        $gameHeartbeat = if ($null -ne $connected) { $connected.game_heartbeat_hz } else { $null }
        $gates = [ordered]@{
            frame_p95_regression_ms = $frameRegression
            frame_p95_within_1_ms = if ($null -ne $frameRegression) { $frameRegression -le 1.0 } else { $null }
            normalized_cpu_p95_regression_pct = $cpuRegression
            normalized_cpu_within_2_points = if ($null -ne $cpuRegression) { $cpuRegression -le 2.0 } else { $null }
            connected_private_memory_growth_bytes = $memoryGrowth
            connected_memory_within_32_mib = if ($null -ne $memoryGrowth) { $memoryGrowth -le 33554432 } else { $null }
            connected_client_heartbeat_hz = $clientHeartbeat
            connected_client_heartbeat_near_1_hz = if ($null -ne $clientHeartbeat) { $clientHeartbeat -ge 0.8 -and $clientHeartbeat -le 1.2 } else { $null }
            connected_game_heartbeat_hz = $gameHeartbeat
            connected_game_heartbeat_near_1_hz = if ($null -ne $gameHeartbeat) { $gameHeartbeat -ge 0.8 -and $gameHeartbeat -le 1.2 } else { $null }
        }
        $report = [ordered]@{
            schema_version = $scriptVersion
            generated_at_utc = Get-UtcTimestamp
            source_sha256 = Get-Sha256 $source
            groups = $groupResults
            frame_groups = $frameResults
            gates = $gates
        }
        $reportPath = Join-Path $resolvedOutput "analysis.json"
        [System.IO.File]::WriteAllText($reportPath, ($report | ConvertTo-Json -Depth 10), $utf8)
        Write-Output $reportPath
    }
}
