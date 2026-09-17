# Install dependencies and cache model weights before starting any server.
# Prefer the project runtime so setup does not replace system Python.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
try {
    $projectPython = Join-Path $PSScriptRoot "env\Scripts\python.exe"
    if (-not (Test-Path $projectPython)) {
        $projectPython = Join-Path $PSScriptRoot ".tools\python312\python.exe"
    }
    if (Test-Path $projectPython) {
        & $projectPython run.py --device auto --setup-only
    } else {
        py -3.12 run.py --device auto --setup-only
    }
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
    Write-Host "Downloading model weights, this may take several minutes..."
    & "$PSScriptRoot\env\Scripts\python.exe" -m app.cache_model
    if ($LASTEXITCODE -ne 0) { throw "Model caching failed; setup is incomplete. Check the error above and retry." }
    Write-Host "Setup complete. Run run.bat to start the server."
} catch {
    Write-Error "Setup failed: $_"
    exit 1
}
