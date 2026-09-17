Write-Host "========================================" -ForegroundColor Yellow
Write-Host ">>> STARTING DEVACIA BACKEND (STAGING) <<<" -ForegroundColor Yellow
Write-Host "- Environment: staging" -ForegroundColor Cyan
Write-Host "- Discovery Mode: mock (no live API credits used)" -ForegroundColor Cyan
Write-Host "- API Port: 8000" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Yellow

 = Split-Path -Parent System.Management.Automation.InvocationInfo.MyCommand.Path
 = Join-Path  ".env.staging"

if (Test-Path ) {
    Get-Content  | ForEach-Object {
         = .Trim()
        if ( -and -not .StartsWith("#") -and  -match '^\s*([^=]+)=(.*)$') {
             = [1].Trim()
             = [2].Trim().Trim('"').Trim("'")
            [System.Environment]::SetEnvironmentVariable(, , "Process")
        }
    }
}

 = "staging"
if (-not ) {
     = "mock"
}

 = Join-Path  "venv312\Scripts\python.exe"
 = Join-Path  "venv312\Scripts\uvicorn.exe"

if (-not (Test-Path )) {
     = "uvicorn"
}

Write-Host "Starting Uvicorn staging server on port 8000 with auto-reload..." -ForegroundColor Green
&  main:app --host 0.0.0.0 --port 8000 --reload
