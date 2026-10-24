Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "Starting RoadMind AI Backend (FastAPI on Port 8000)" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Cyan

python "$PSScriptRoot\backend\app\main.py"
