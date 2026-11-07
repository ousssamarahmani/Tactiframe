param(
    [Parameter(Mandatory = $true)]
    [string]$BaselineRunDir,
    [Parameter(Mandatory = $true)]
    [string]$CandidateRunDir,
    [ValidateRange(0.1, 60.0)]
    [double]$LostTrackBufferSeconds = 8.0
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSCommandPath
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$baseline = (Resolve-Path $BaselineRunDir).Path
$candidate = Join-Path $repoRoot $CandidateRunDir
if (Test-Path -LiteralPath $candidate) {
    throw "Candidate output already exists; choose a new directory: $candidate"
}

$metadata = Get-Content (Join-Path $baseline "run.json") -Raw | ConvertFrom-Json
if ($metadata.status -ne "observations-only") {
    throw "Baseline perception is not complete: $($metadata.status)"
}
$video = $metadata.video.path
$model = $metadata.model.path
$polygon = $metadata.parameters.fieldPolygons
if (-not (Test-Path -LiteralPath $video) -or -not (Test-Path -LiteralPath $model) -or -not (Test-Path -LiteralPath $polygon)) {
    throw "Baseline video, model, or field polygon is missing locally."
}

$env:YOLO_CONFIG_DIR = Join-Path $repoRoot "data\ultralytics"
& $python run_pipeline.py --video $video --model $model --field-polygons $polygon `
    --output-dir $candidate --lost-track-buffer-seconds $LostTrackBufferSeconds
& $python detect_events.py --run-dir $candidate

# This is a CV experiment; prevent an AWS/Bedrock invocation or cloud upload.
$priorAws = $env:AWS_ENABLED
$env:AWS_ENABLED = "false"
try {
    & $python run_agent.py --run-dir $candidate
} finally {
    if ($null -eq $priorAws) { Remove-Item Env:AWS_ENABLED -ErrorAction SilentlyContinue }
    else { $env:AWS_ENABLED = $priorAws }
}

& $python validate_ball_candidates.py --run-dir $candidate
& $python diagnose_tracks.py --run-dir $candidate --window-seconds 30
& $python evaluate_session.py --run-dir $candidate
& $python compare_tracking_runs.py --baseline-run-dir $baseline --candidate-run-dir $candidate
