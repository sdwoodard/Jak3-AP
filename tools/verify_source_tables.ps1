[CmdletBinding()]
param(
    [string] $OpenGoalRoot = (Join-Path $PSScriptRoot "..\..\jak-project")
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$designPath = Join-Path $repositoryRoot "docs\design\progression-and-logic.md"
$resolvedRoot = (Resolve-Path -LiteralPath $OpenGoalRoot).Path
$sourceCandidates = @(
    (Join-Path $resolvedRoot "goal_src\jak3\engine\game\task"),
    (Join-Path $resolvedRoot "data\goal_src\jak3\engine\game\task")
)
$taskRoot = $sourceCandidates | Where-Object {
    Test-Path -LiteralPath (Join-Path $_ "game-task.gc") -PathType Leaf
} | Select-Object -First 1
if (-not $taskRoot) {
    throw "Could not find goal_src/jak3/engine/game/task below $resolvedRoot"
}

$header = Get-Content -Raw -LiteralPath (Join-Path $taskRoot "game-task-h.gc")
$source = Get-Content -Raw -LiteralPath (Join-Path $taskRoot "game-task.gc")
$design = Get-Content -LiteralPath $designPath
$failures = [System.Collections.Generic.List[string]]::new()

function Fail([string] $Message) {
    $failures.Add($Message)
}

function Hex-Or-Decimal([string] $Value) {
    if (-not $Value) { return 0 }
    if ($Value.StartsWith("#x")) { return [Convert]::ToInt32($Value.Substring(2), 16) }
    return [int] $Value
}

# Native task enum.
$taskSection = $header.Substring($header.IndexOf("(defenum game-task"))
$taskSection = $taskSection.Substring(0, $taskSection.IndexOf(";; ---game-task"))
$taskById = @{}
$idByTask = @{}
foreach ($match in [regex]::Matches($taskSection, '(?m)^\s*\(([a-z0-9-]+)\s+(-?\d+)\)')) {
    $name = $match.Groups[1].Value
    $id = [int] $match.Groups[2].Value
    $taskById[$id] = $name
    $idByTask[$name] = $id
}

# Native node enum and node records.
$nodeSection = $header.Substring($header.IndexOf("(defenum game-task-node"))
$nodeSection = $nodeSection.Substring(0, $nodeSection.IndexOf(";; ---game-task-node"))
$nodeNames = @([regex]::Matches($nodeSection, '(?m)^\s*\(([a-z0-9-]+)(?:\s+-?\d+)?\)') |
    ForEach-Object { $_.Groups[1].Value })
$segments = @([regex]::Split($source, "\(new 'static 'game-task-node-info") | Select-Object -Skip 1)
$nodeRecords = @{}
$closeByTask = @{}
foreach ($segment in $segments) {
    $name = [regex]::Match($segment, ':name\s+"([^"]+)"').Groups[1].Value
    if (-not $name) { continue }
    $task = [regex]::Match($segment, ':task\s+\(game-task\s+([^)]+)\)').Groups[1].Value
    $flags = [regex]::Match($segment, ':flags\s+\(game-task-node-flag\s+([^)]+)\)').Groups[1].Value
    $parent = [regex]::Match($segment, '(?s):parent-node.*?\(game-task-node\s+([^)]+)\)').Groups[1].Value
    $commandIndex = Hex-Or-Decimal ([regex]::Match(
        $segment, ':command-index\s+(#x[0-9a-f]+|\d+)').Groups[1].Value)
    $commandCount = Hex-Or-Decimal ([regex]::Match(
        $segment, ':command-count\s+(#x[0-9a-f]+|\d+)').Groups[1].Value)
    $nodeRecords[$name] = [pscustomobject]@{
        Name = $name
        Task = $task
        Flags = @($flags -split '\s+' | Where-Object { $_ })
        Parent = $parent
        CommandIndex = $commandIndex
        CommandCount = $commandCount
    }
    if ($flags -split '\s+' -contains "close-task") {
        if (-not $closeByTask.ContainsKey($task)) { $closeByTask[$task] = @() }
        $closeByTask[$task] += $name
    }
}

# Reward command list, indexed by each node record.
$commandSection = $source.Substring($source.IndexOf("(set! (-> game-info task-node-commands)"))
$commands = @([regex]::Matches($commandSection, '\(game-task-node-command\s+([a-z0-9-]+)\)') |
    ForEach-Object { $_.Groups[1].Value })
$rewardRecords = @($nodeRecords.Values | Where-Object { $_.CommandCount -gt 0 })

if ($taskById.Count -lt 139) { Fail "Task enum is unexpectedly short ($($taskById.Count) entries)." }
if ($nodeNames.Count -ne 410) { Fail "Expected 410 task-node enum entries; found $($nodeNames.Count)." }
if ($nodeRecords.Count -ne 410) { Fail "Expected 410 task-node records; found $($nodeRecords.Count)." }
if ($commands.Count -ne 75) { Fail "Expected 75 native reward commands; found $($commands.Count)." }
if ($rewardRecords.Count -ne 51) { Fail "Expected 51 reward-bearing nodes; found $($rewardRecords.Count)." }

# Mission table rows (6-72) and side-task table rows (73-137).
$designTaskRows = @{}
$sideLines = @{}
$inMissionTable = $false
$inSideTable = $false
foreach ($line in $design) {
    if ($line -like "## 9. Mission-by-mission*") { $inMissionTable = $true; continue }
    if ($line -like "### 9.1*") { $inMissionTable = $false }
    if ($line -like "### 11.4 Side-mission*") { $inSideTable = $true; continue }
    if ($line -like "### 11.5*") { $inSideTable = $false }
    if (-not ($inMissionTable -or $inSideTable)) { continue }
    $fields = @($line -split '\|' | ForEach-Object { $_.Trim() })
    if ($fields.Count -lt 5 -or $fields[1] -notmatch '^\d+$') { continue }
    $id = [int] $fields[1]
    if (($id -ge 6 -and $id -le 72) -or ($id -ge 73 -and $id -le 137)) {
        $alias = $fields[3].Trim('`')
        if ($alias -match '^[a-z0-9-]+$') {
            $designTaskRows[$id] = $alias
            if ($inSideTable) { $sideLines[$id] = $line }
        }
    }
}
foreach ($id in 6..137) {
    if (-not $designTaskRows.ContainsKey($id)) {
        Fail "Design is missing task row $id."
        continue
    }
    $expected = $taskById[$id]
    $actual = $designTaskRows[$id]
    if ($id -eq 88) {
        if ($actual -ne "wascity-bbush-get-to-19") {
            Fail "Task 88 must use normalized node alias wascity-bbush-get-to-19 in the design."
        }
    } elseif ($actual -ne $expected) {
        Fail "Task $id alias mismatch: design=$actual source=$expected."
    }
}

# Every story completion row has a source close flag except the documented task 36.
foreach ($id in 6..72) {
    $task = $taskById[$id]
    $hasClose = $closeByTask.ContainsKey($task)
    if ($id -eq 36 -and $hasClose) { Fail "Task 36 unexpectedly gained a close-task node; re-audit it." }
    if ($id -ne 36 -and -not $hasClose) { Fail "Story task $id ($task) has no close-task node." }
}
foreach ($id in 73..137) {
    $task = $taskById[$id]
    if (-not $closeByTask.ContainsKey($task)) { Fail "Side task $id ($task) has no close-task node." }
}

# Reward-sanity rows must cover every source reward node exactly once.
$rewardDesignRows = @{}
$inRewardTable = $false
foreach ($line in $design) {
    if ($line -like "### 11.2 Native reward*") { $inRewardTable = $true; continue }
    if ($line -like "### 11.3*") { $inRewardTable = $false }
    if (-not $inRewardTable) { continue }
    $fields = @($line -split '\|' | ForEach-Object { $_.Trim() })
    if ($fields.Count -lt 7 -or $fields[1] -notmatch '^\d+$') { continue }
    $id = [int] $fields[1]
    $node = $fields[2].Trim('`')
    if ($nodeRecords.ContainsKey($node) -and $nodeRecords[$node].CommandCount -gt 0) {
        $rewardDesignRows[$id] = $node
    }
}
foreach ($record in $rewardRecords) {
    $nodeId = [array]::IndexOf($nodeNames, $record.Name)
    if (-not $rewardDesignRows.ContainsKey($nodeId)) {
        Fail "Design reward table is missing node $nodeId ($($record.Name))."
    } elseif ($rewardDesignRows[$nodeId] -ne $record.Name) {
        Fail "Reward node $nodeId mismatch: design=$($rewardDesignRows[$nodeId]) source=$($record.Name)."
    }
}

# Default side-task parents are source-verifiable even though AP adds capability gates.
foreach ($id in 114..137) {
    $alias = $designTaskRows[$id]
    $introName = "$alias-introduction"
    $record = $nodeRecords[$introName]
    if (-not $record) { Fail "No introduction node found for selected side task $id ($alias)."; continue }
    $parentRecord = $nodeRecords[$record.Parent]
    if (-not $parentRecord) { Fail "No source parent record found for selected side task $id."; continue }
    $line = $sideLines[$id]
    $declared = [regex]::Match($line, '\| task (\d+) \|').Groups[1].Value
    if (-not $declared) { Fail "Design does not name a source parent task for selected side task $id."; continue }
    if ([int] $declared -ne $idByTask[$parentRecord.Task]) {
        Fail "Selected side task $id parent mismatch: design=$declared source=$($idByTask[$parentRecord.Task])."
    }
}

# Milestone candidates must be real nodes attached to the stated native task.
$inMilestones = $false
foreach ($line in $design) {
    if ($line -eq "Candidate whitelist:") { $inMilestones = $true; continue }
    if ($inMilestones -and $line -like "### *") { break }
    if (-not $inMilestones) { continue }
    $fields = @($line -split '\|' | ForEach-Object { $_.Trim() })
    if ($fields.Count -lt 5 -or $fields[1] -notmatch '^\d+$') { continue }
    $taskId = [int] $fields[1]
    $nodeName = $fields[2].Trim('`')
    if (-not $nodeRecords.ContainsKey($nodeName)) { Fail "Milestone node $nodeName does not exist."; continue }
    if ($idByTask[$nodeRecords[$nodeName].Task] -ne $taskId) {
        Fail "Milestone $nodeName belongs to task $($idByTask[$nodeRecords[$nodeName].Task]), not $taskId."
    }
}

$majorCount = @($design | Where-Object { $_ -match '\| Major \(default\) \|' }).Count
$crystalCount = @($design | Where-Object { $_ -match '\| All-stable only \|' }).Count
$neverCount = @($design | Where-Object { $_ -match '\| Never \|' }).Count
if ($majorCount -ne 38) { Fail "Expected 38 Major reward rows; found $majorCount." }
if ($crystalCount -ne 8) { Fail "Expected 8 crystal-only reward rows; found $crystalCount." }
if ($neverCount -ne 5) { Fail "Expected 5 never-valid reward rows; found $neverCount." }

if ($failures.Count) {
    Write-Error ("Jak 3 source-table audit failed:`n- " + ($failures -join "`n- "))
    exit 1
}

Write-Output "PASS: task IDs and aliases 6-137 match the source (task 88 normalized)."
Write-Output "PASS: story close-task coverage matches the design; task 36 is the only omission."
Write-Output "PASS: all 65 side tasks have close-task records."
Write-Output "PASS: all 51 reward nodes are accounted for (38 major, 8 crystal-only, 5 never)."
Write-Output "PASS: all 24 selected side-task source parents match."
Write-Output "PASS: every candidate milestone node exists on its documented task."
Write-Output "Audited source: $taskRoot"
