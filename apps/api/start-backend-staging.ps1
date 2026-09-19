$ErrorActionPreference = 'Stop'
$apiRoot = $PSScriptRoot
$env:APP_ENV_FILE = Join-Path $apiRoot '.env.staging'
$env:PYTHONDONTWRITEBYTECODE = '1'
Set-Location -LiteralPath $apiRoot
$pythonPath = Join-Path $apiRoot 'venv312\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Install the API requirements in apps/api/venv312 first.' }
& $pythonPath -m uvicorn main:app --host 127.0.0.1 --port 8000
