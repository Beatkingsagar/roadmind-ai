@echo off
title RoadMind AI - Launcher
echo ====================================================
echo Launching RoadMind AI (Backend + Frontend)
echo ====================================================
start "RoadMind AI Backend" cmd /k "run_backend.bat"
timeout /t 2 /nobreak >nul
start "RoadMind AI Frontend" cmd /k "run_frontend.bat"
echo.
echo Both servers have been launched in separate terminal windows!
echo - Web Dashboard:  http://localhost:5173
echo - API Docs (Swagger): http://127.0.0.1:8000/docs
echo ====================================================
pause
