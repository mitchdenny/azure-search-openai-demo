$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$venvPythonPath = "./.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./.venv/bin/python"
}

& $venvPythonPath ./app/backend/prepdocs.py './data/*' --verbose @args
exit $LASTEXITCODE
