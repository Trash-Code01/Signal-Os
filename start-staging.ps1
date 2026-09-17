# ==============================================================================
# Devacia OS - Staging Development Runner
# Boots local staging stack completely isolated from live production data.
# Frontend: http://localhost:3001
# Backend:  http://localhost:8000
# ==============================================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host "    DEVACIA INTELLIGENCE OS - STAGING DEVELOPMENT MODE      " -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host " [SAFE SANDBOX] No live production data or API credits used. " -ForegroundColor Cyan
Write-Host ""

 = Split-Path -Parent System.Management.Automation.InvocationInfo.MyCommand.Path
 = Join-Path  "apps\api"
 = Join-Path  "apps\web"

# 1. Check Docker status (optional helper)
Write-Host "[1/3] Checking Docker / Database services..." -ForegroundColor Cyan
try {
     = docker ps 2>&1
    if ( -eq 0) {
        Write-Host " Docker daemon is active." -ForegroundColor Green
    } else {
        Write-Host " Docker daemon not detected. Using native/existing PostgreSQL service if running." -ForegroundColor DarkYellow
    }
} catch {
    Write-Host " Docker check skipped." -ForegroundColor DarkGray
}

# 2. Start Backend in Staging Mode (Port 8000)
Write-Host "[2/3] Launching FastAPI Backend in Staging Mode (Port 8000)..." -ForegroundColor Cyan
 = Join-Path  "start-backend-staging.ps1"
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", """"

# 3. Start Frontend in Staging Mode (Port 3001)
Write-Host "[3/3] Launching Next.js Frontend on PORT 3001..." -ForegroundColor Cyan
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " Staging App URL:  http://localhost:3001" -ForegroundColor Green
Write-Host " Staging API URL:  http://localhost:8000" -ForegroundColor Green
Write-Host " Admin Login:      admin@devacia.com / admin123" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Set-Location 
npm run dev:staging
