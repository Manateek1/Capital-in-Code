$ErrorActionPreference = "Stop"

$projectDirectory = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $projectDirectory ".venv\Scripts\cyclequant.exe"

if (-not (Test-Path -LiteralPath $runner)) {
    throw "CycleQuant is not installed in $projectDirectory\.venv"
}

Push-Location $projectDirectory
try {
    & $runner daily
    if ($LASTEXITCODE -ne 0) {
        throw "CycleQuant daily evaluation failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
