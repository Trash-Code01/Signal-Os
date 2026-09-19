Write-Host "Starting Devacia OS Backend natively..." -ForegroundColor Green

$env:DATABASE_URL = "postgresql+psycopg://devacia:devacia_password@localhost:5432/devacia_os"
$env:REDIS_URL = "redis://localhost:6379/0"

Write-Host "Starting API on port 8000..." -ForegroundColor Cyan
Start-Process -NoNewWindow -FilePath ".\venv312\Scripts\uvicorn.exe" -ArgumentList "main:app --host 0.0.0.0 --port 8000"

Write-Host "Starting Celery Worker..." -ForegroundColor Cyan
Start-Process -NoNewWindow -FilePath ".\venv312\Scripts\celery.exe" -ArgumentList "-A worker.celery_app worker --loglevel=info -P threads"

Write-Host "Native backend started successfully." -ForegroundColor Green
