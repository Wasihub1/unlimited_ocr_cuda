# Bootstrap Python 3.12 and stop immediately on any failed setup step.
param([Parameter(ValueFromRemainingArguments=$true)][string[]]$LauncherArgs)
$ErrorActionPreference = 'Stop'

function Find-Python312 {
    $candidates = @(
        @{Exe='py'; Prefix=@('-3.12')},
        @{Exe='python'; Prefix=@()},
        @{Exe=(Join-Path $PSScriptRoot 'env\Scripts\python.exe'); Prefix=@()},
        @{Exe=(Join-Path $PSScriptRoot '.tools\python312\python.exe'); Prefix=@()},
        @{Exe=(Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'); Prefix=@()}
    )
    foreach ($candidate in $candidates) {
        if (-not (Get-Command $candidate.Exe -ErrorAction SilentlyContinue)) { continue }
        try {
            $prefix = $candidate.Prefix
            $found = & $candidate.Exe @prefix -c 'import sys; print(sys.executable if sys.version_info[:2] == (3,12) else str())' 2>$null
            if ($LASTEXITCODE -eq 0 -and $found -and (Test-Path -LiteralPath $found)) { return $found }
        } catch { continue }
    }
    return $null
}

function Install-Python312 {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        & winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements | Out-Host
        $found = Find-Python312
        if ($found) { return $found }
        Write-Host 'winget did not provide Python 3.12; trying the official installer.'
    }
    $installer = Join-Path $PSScriptRoot 'logs\python-3.12.10-amd64.exe'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile $installer -UseBasicParsing
    $signature = Get-AuthenticodeSignature -FilePath $installer
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
        throw 'Official Python installer signature could not be verified.'
    }
    $install = Start-Process -FilePath $installer -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1' -WindowStyle Hidden -Wait -PassThru
    if ($install.ExitCode -notin @(0, 3010)) { throw "Python installer exited with code $($install.ExitCode)" }
    $found = Find-Python312
    if (-not $found) { throw 'Python 3.12 could not be found after installation.' }
    return $found
}

function Initialize-Environment([string]$Python) {
    $envFolder = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'env'))
    $envPython = Join-Path $envFolder 'Scripts\python.exe'
    $valid = $false
    if (Test-Path -LiteralPath $envPython) {
        & $envPython -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3,12) else 1)'
        $valid = $LASTEXITCODE -eq 0
    }
    if (-not $valid) {
        if (Test-Path -LiteralPath $envFolder) {
            # Retain the old environment; never recursively delete user contents.
            if ([IO.Path]::GetDirectoryName($envFolder) -ne [IO.Path]::GetFullPath($PSScriptRoot)) { throw 'Environment is outside the project.' }
            $backup = Join-Path $PSScriptRoot ('env.backup-' + [guid]::NewGuid().ToString('N'))
            Move-Item -LiteralPath $envFolder -Destination $backup
            Write-Host "Previous environment retained at $backup"
        }
        & $Python -m venv $envFolder
        if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
    } else { Write-Host 'Python 3.12 environment already exists.' }
    return $envPython
}

# Dot sourcing exposes functions for isolated tests without installing anything.
if ($MyInvocation.InvocationName -eq '.') { return }
$step = 'logging'
$transcript = $false
try {
    Set-Location $PSScriptRoot
    New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot 'logs') | Out-Null
    Start-Transcript -Path (Join-Path $PSScriptRoot 'logs\setup.log') -Append | Out-Null
    $transcript = $true
    $env:UNO_SETUP_TRANSCRIPT = '1'
    $env:HF_HUB_DISABLE_SYMLINKS_WARNING = '1'
    $env:HF_HUB_DISABLE_TELEMETRY = '1'
    $step = 'Python 3.12 detection/install'
    $python = Find-Python312
    if (-not $python) { $python = Install-Python312 }
    $step = 'virtual environment'
    $envPython = Initialize-Environment $python
    $step = 'dependencies and model cache'
    & $envPython (Join-Path $PSScriptRoot 'run.py') --setup-only @LauncherArgs
    if ($LASTEXITCODE -ne 0) { throw 'run.py setup failed; see the specific step and underlying error above.' }
} catch {
    Write-Host "Setup failed at step ${step}: $_" -ForegroundColor Red
    exit 1
} finally {
    if ($transcript) { Stop-Transcript | Out-Null }
}
exit 0
