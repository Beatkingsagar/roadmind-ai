Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "Starting RoadMind AI Frontend (Vite on Port 5173)" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Cyan

Set-Location -Path "$PSScriptRoot\apps\web"
bun run dev --port 5173
