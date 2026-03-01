param(
    [ValidateSet('onefile','onedir')]
    [string]$Mode = 'onedir',

    [switch]$Console
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    throw "Expected venv python at: $python. Create the venv and install requirements first."
}

# Use separate output folders to avoid clobbering the repo's existing build/ (pygbag).
$workPath = Join-Path $repoRoot 'pyinstaller-build'
$distPath = Join-Path $repoRoot 'pyinstaller-dist'

# Ensure PyInstaller is installed in the venv.
& $python -m pip show pyinstaller *> $null
if ($LASTEXITCODE -ne 0) {
    & $python -m pip install pyinstaller
}

$windowFlag = @('--windowed')
if ($Console) { $windowFlag = @() }

$modeFlag = @('--onedir')
if ($Mode -eq 'onefile') { $modeFlag = @('--onefile') }

# Bundle assets next to the packaged python modules.
# NOTE: On Windows, PyInstaller uses ';' as the add-data separator.
$addData = @(
    '--add-data', 'src\\choplifter\\assets;src\\choplifter\\assets'
)

& $python -m PyInstaller `
    --noconfirm `
    $modeFlag `
    $windowFlag `
    --name Choplifter `
    --specpath $workPath `
    --workpath $workPath `
    --distpath $distPath `
    $addData `
    run.py

Write-Host "Build complete: $distPath"