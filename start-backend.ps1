Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "DEVACIA LEAD INTELLIGENCE OS" -ForegroundColor Cyan
Write-Host "Backend Initialization Script" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

cd apps\api

Write-Host "[1/3] Creating virtual environment & installing dependencies..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    python -m venv venv
}
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

Write-Host ""
Write-Host "[2/3] Initializing Playwright (Chromium)..." -ForegroundColor Yellow
Write-Host "Note: If this fails due to a network timeout, try running it manually: playwright install chromium" -ForegroundColor Gray
playwright install chromium

Write-Host ""
Write-Host "[3/3] Starting backend services..." -ForegroundColor Yellow
Write-Host "The API safely initializes the CRM workspace tables on startup." -ForegroundColor Gray
Write-Host "Starting FastAPI Server on port 8000..." -ForegroundColor Green
Start-Process -NoNewWindow -FilePath "uvicorn" -ArgumentList "main:app --reload --port 8000"

Write-Host "Starting Celery Worker..." -ForegroundColor Green
Start-Process -NoNewWindow -FilePath "celery" -ArgumentList "-A worker.celery_app worker --loglevel=info -P threads"

Write-Host ""
Write-Host "Backend is running!" -ForegroundColor Green
Write-Host "Make sure Docker Compose (Postgres + Redis) is also running." -ForegroundColor Cyan
