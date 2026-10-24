Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "Launching RoadMind AI (Backend + Frontend)" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Cyan

Start-Process powershell -ArgumentList "-NoExit", "-File", "$PSScriptRoot\run_backend.ps1"
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-File", "$PSScriptRoot\run_frontend.ps1"

Write-Host "Services launched in separate windows!" -ForegroundColor Yellow
Write-Host "- Web Dashboard:  http://localhost:5173" -ForegroundColor White
Write-Host "- API Docs:       http://127.0.0.1:8000/docs" -ForegroundColor White
