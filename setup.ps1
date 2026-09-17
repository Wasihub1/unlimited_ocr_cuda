$ErrorActionPreference = "Stop"

Write-Host "Checking for Python 3.12..."
$hasPython312 = $false
try {
    py -3.12 --version | Out-Null
    if ($LASTEXITCODE -eq 0) { $hasPython312 = $true }
} catch {}

if (-not $hasPython312) {
    Write-Host "Python 3.12 not found. Downloading installer..."
    $installerUrl = "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
    $installerPath = "$env:TEMP\python-3.12.7-installer.exe"
    Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath
    Write-Host "Installing Python 3.12 (silent)..."
    Start-Process -FilePath $installerPath -Args "/quiet InstallAllUsers=1 PrependPath=1 Include_launcher=1" -Wait
    Write-Host "Please close and reopen PowerShell, then run this script again."
    exit
}

Write-Host "Python 3.12 found. Setting up environment..."
py -3.12 run.py --device auto