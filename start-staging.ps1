$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$apiRoot = Join-Path $projectRoot 'apps\api'
$webRoot = Join-Path $projectRoot 'apps\web'
$logRoot = Join-Path $projectRoot '.staging-logs'
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
foreach ($port in @(8000, 3001)) {
    $probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
    try { $probe.Start() }
    catch { throw "Cannot bind port $port. Stop its existing service before starting staging." }
    finally { $probe.Stop() }
}
$backendScript = Join-Path $apiRoot 'start-backend-staging.ps1'
$frontendScript = Join-Path $webRoot 'start-web-staging.ps1'
$backend = Start-Process powershell.exe -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', "& '$backendScript'") -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logRoot 'api.out.log') -RedirectStandardError (Join-Path $logRoot 'api.err.log')
$frontend = Start-Process powershell.exe -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', "& '$frontendScript'") -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logRoot 'web.out.log') -RedirectStandardError (Join-Path $logRoot 'web.err.log')
@{backend=$backend.Id; frontend=$frontend.Id} | ConvertTo-Json | Set-Content (Join-Path $logRoot 'processes.json')
Write-Host 'Staging starting at http://127.0.0.1:3001 with an isolated SQLite database and mock jobs.'
Write-Host 'Google configuration: apps/api/.env.staging.local. Logs: .staging-logs.'
