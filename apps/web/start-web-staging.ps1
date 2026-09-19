$ErrorActionPreference = 'Stop'
$webRoot = $PSScriptRoot
$env:NEXT_PUBLIC_APP_ENV = 'staging'
$env:NEXT_PUBLIC_API_URL = 'http://localhost:8000'
Set-Location -LiteralPath $webRoot
$node = (Get-Command node.exe).Source
& $node 'node_modules/next/dist/bin/next' 'dev' '-p' '3001' '--hostname' '127.0.0.1'
