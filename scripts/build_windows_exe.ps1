param(
    [ValidateSet('onefile','onedir')]
    [string]$Mode = 'onedir',

    [switch]$Console,

    # Optional Authenticode signing. This is the primary way to reduce/remove
    # SmartScreen warnings for public distribution.
    [switch]$Sign,

    # Sign using a PFX file.
    [string]$PfxPath,

    # If provided, read the PFX password from this environment variable.
    # Example: $env:CHOPLIFTER_PFX_PASSWORD = '...'
    [string]$PfxPasswordEnvVar = 'CHOPLIFTER_PFX_PASSWORD',

    # Alternatively, sign using a certificate already installed in the Windows cert store.
    # Provide the SHA1 thumbprint (no spaces).
    [string]$CertThumbprint,

    # RFC3161 timestamp server. Timestamping is important so the signature remains valid
    # after the code signing certificate expires.
    [string]$TimestampUrl = 'http://timestamp.digicert.com'
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
$assetsSrc = Join-Path $repoRoot 'src\choplifter\assets'
$stagedAssets = Join-Path $workPath 'asset-staging'

# Explicit runtime asset manifest. Keep this list tight so source art files
# (for example .xcf) do not silently inflate distributable builds.
$assetIncludeExtensions = @(
    '.png',
    '.jpg',
    '.jpeg',
    '.ogg',
    '.avi',
    '.mpg',
    '.json'
)

$allAssetFiles = Get-ChildItem -Path $assetsSrc -Recurse -File
$xcfSourceAssets = $allAssetFiles | Where-Object { $_.Extension.ToLowerInvariant() -eq '.xcf' }

if (Test-Path $stagedAssets) {
    Remove-Item -Recurse -Force $stagedAssets
}
New-Item -ItemType Directory -Path $stagedAssets | Out-Null

$includedAssets = $allAssetFiles |
    Where-Object { $assetIncludeExtensions -contains $_.Extension.ToLowerInvariant() }

# Prefer modern .avi cutscenes over legacy .mpg files when both exist.
$aviRelPaths = New-Object System.Collections.Generic.HashSet[string] ([System.StringComparer]::OrdinalIgnoreCase)
foreach ($asset in $includedAssets) {
    if ($asset.Extension.ToLowerInvariant() -eq '.avi') {
        $aviRel = $asset.FullName.Substring($assetsSrc.Length).TrimStart('\', '/')
        $aviWithoutExt = [System.IO.Path]::ChangeExtension($aviRel, $null)
        [void]$aviRelPaths.Add($aviWithoutExt)
    }
}

$includedAssets = $includedAssets | Where-Object {
    if ($_.Extension.ToLowerInvariant() -ne '.mpg') {
        return $true
    }
    $mpgRel = $_.FullName.Substring($assetsSrc.Length).TrimStart('\', '/')
    $mpgWithoutExt = [System.IO.Path]::ChangeExtension($mpgRel, $null)
    return -not $aviRelPaths.Contains($mpgWithoutExt)
}

foreach ($asset in $includedAssets) {
    $relativePath = $asset.FullName.Substring($assetsSrc.Length).TrimStart('\', '/')
    $targetPath = Join-Path $stagedAssets $relativePath
    $targetDir = Split-Path -Parent $targetPath
    if (-not (Test-Path $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir | Out-Null
    }
    Copy-Item -LiteralPath $asset.FullName -Destination $targetPath -Force
}

$stagedXcfAssets = @()
if (Test-Path $stagedAssets) {
    $stagedXcfAssets = Get-ChildItem -Path $stagedAssets -Recurse -File -Filter '*.xcf'
}
if ($stagedXcfAssets.Count -gt 0) {
    $badPaths = ($stagedXcfAssets | ForEach-Object { $_.FullName.Substring($stagedAssets.Length).TrimStart('\', '/') }) -join ', '
    throw "Build staging validation failed: .xcf files must not be packaged, but found: $badPaths"
}

Write-Host ("ASSET_STAGING: included={0} | excluded_xcf={1} | from={2}" -f $includedAssets.Count, $xcfSourceAssets.Count, $assetsSrc)

$addData = @(
    '--add-data', "$stagedAssets;src\\choplifter\\assets"
)

& $python -m PyInstaller `
    --noconfirm `
    $modeFlag `
    $windowFlag `
    --name Choplifter `
    --specpath $workPath `
    --workpath $workPath `
    --distpath $distPath `
    --copy-metadata imageio `
    --copy-metadata imageio-ffmpeg `
    --collect-data imageio_ffmpeg `
    $addData `
    run.py

function Resolve-SignToolPath {
    # Prefer user-provided path.
    if ($env:SIGNTOOL_PATH -and (Test-Path $env:SIGNTOOL_PATH)) {
        return $env:SIGNTOOL_PATH
    }

    # Try common Windows SDK locations.
    $sdkRoot = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin'
    if (Test-Path $sdkRoot) {
        $candidates = Get-ChildItem -Path $sdkRoot -Directory -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            ForEach-Object {
                @(
                    (Join-Path $_.FullName 'x64\signtool.exe'),
                    (Join-Path $_.FullName 'x86\signtool.exe')
                )
            } |
            Where-Object { Test-Path $_ }

        if ($candidates -and $candidates.Count -gt 0) {
            return $candidates[0]
        }
    }

    # Fall back to PATH.
    $cmd = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    return $null
}

function Get-OutputExePath([string]$distPath, [string]$mode) {
    if ($mode -eq 'onefile') {
        return (Join-Path $distPath 'Choplifter.exe')
    }
    return (Join-Path $distPath 'Choplifter\Choplifter.exe')
}

if ($Sign) {
    $exePath = Get-OutputExePath -distPath $distPath -mode $Mode
    if (-not (Test-Path $exePath)) {
        throw "Expected output EXE not found at: $exePath"
    }

    $signtool = Resolve-SignToolPath
    if (-not $signtool) {
        throw "signtool.exe not found. Install the Windows SDK (Signing Tools) or set SIGNTOOL_PATH to signtool.exe."
    }

    $signArgs = @(
        'sign',
        '/v',
        '/fd', 'sha256',
        '/tr', $TimestampUrl,
        '/td', 'sha256'
    )

    if ($PfxPath) {
        if (-not (Test-Path $PfxPath)) {
            throw "PfxPath not found: $PfxPath"
        }
        $signArgs += @('/f', $PfxPath)

        if ($PfxPasswordEnvVar) {
            $pfxPassword = [Environment]::GetEnvironmentVariable($PfxPasswordEnvVar)
            if ($pfxPassword) {
                $signArgs += @('/p', $pfxPassword)
            }
        }
    }
    elseif ($CertThumbprint) {
        $thumb = ($CertThumbprint -replace '\s', '')
        $signArgs += @('/sha1', $thumb)
    }
    else {
        throw "Signing requested but neither -PfxPath nor -CertThumbprint was provided."
    }

    $signArgs += @($exePath)

    Write-Host "Signing: $exePath"
    & $signtool @signArgs
    if ($LASTEXITCODE -ne 0) {
        throw "signtool failed with exit code: $LASTEXITCODE"
    }
}

Write-Host "Build complete: $distPath"