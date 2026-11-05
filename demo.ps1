<#!
.SYNOPSIS
Runs the TactiFrame evidence → coach-review demonstration for one completed session.

.DESCRIPTION
The script regenerates the evidence-backed draft plan, briefly starts the local
review API, reads the session artifacts through HTTP, then records the named
coach's explicit decision through the API. It never fabricates an approval.
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$RunDir,

    [Parameter(Mandatory = $true)]
    [ValidateSet("approved", "rejected")]
    [string]$Decision,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Coach,

    [ValidateRange(1024, 65535)]
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$sessionRoot = (Resolve-Path (Join-Path $repoRoot "data\sessions")).Path
$sessionPath = (Resolve-Path $RunDir).Path
$relativeSession = [System.IO.Path]::GetRelativePath($sessionRoot, $sessionPath)

if ($relativeSession -eq "." -or $relativeSession.StartsWith("..") -or
    [System.IO.Path]::IsPathRooted($relativeSession)) {
    throw "RunDir must be a completed session directly inside data\\sessions."
}

$sessionId = Split-Path -Leaf $sessionPath
$baseUrl = "http://127.0.0.1:$Port"

Write-Host "[1/4] Creating an evidence-backed draft plan for $sessionId"
& $python (Join-Path $repoRoot "run_agent.py") --run-dir $sessionPath
if ($LASTEXITCODE -ne 0) {
    throw "run_agent.py failed. The coach decision was not recorded."
}

Write-Host "[2/4] Starting the local review API"
$server = Start-Process -FilePath $python `
    -ArgumentList @("-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "$Port") `
    -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru

try {
    $healthy = $false
    for ($attempt = 1; $attempt -le 15; $attempt++) {
        try {
            $health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
            if ($health.status -eq "ok") {
                $healthy = $true
                break
            }
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $healthy) {
        throw "The local review API did not become ready."
    }

    Write-Host "[3/4] Reading events, trace, and plan through the API"
    $events = Invoke-RestMethod -Uri "$baseUrl/sessions/$sessionId/events" -Method Get
    $trace = Invoke-RestMethod -Uri "$baseUrl/sessions/$sessionId/trace" -Method Get
    $plan = Invoke-RestMethod -Uri "$baseUrl/sessions/$sessionId/plan" -Method Get
    Write-Host "Candidate events: $($events.events.Count)"
    Write-Host "Trace steps: $($trace.steps.Count)"
    Write-Host "Proposal source: $($plan.proposalSource)"
    Write-Host "Selected evidence event: $($plan.evidence.eventId)"

    Write-Host "[4/4] Recording $Decision by $Coach through the approval API"
    $body = @{ decision = $Decision; coach = $Coach } | ConvertTo-Json -Compress
    $result = Invoke-RestMethod -Uri "$baseUrl/sessions/$sessionId/approval" `
        -Method Post -ContentType "application/json" -Body $body
    Write-Host "Final plan status: $($result.plan.status)"
}
finally {
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id
    }
}
