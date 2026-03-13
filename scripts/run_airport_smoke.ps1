param(
    [switch]$VerboseOutput
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Python executable not found at $pythonExe. Activate/create .venv first."
}

Push-Location $repoRoot
try {
    $pytestArgs = @("-m", "pytest", "-q", "-m", "airport_smoke")
    if ($VerboseOutput) {
        $pytestArgs = @("-m", "pytest", "-m", "airport_smoke")
    }

    Write-Host "Running airport smoke suite..." -ForegroundColor Cyan
    & $pythonExe @pytestArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    Write-Host "Airport smoke suite passed." -ForegroundColor Green
}
finally {
    Pop-Location
}
