@echo off
echo Starting Code Sherpa...
echo ===================================

:: Start backend
echo Starting backend server...
start "Code Sherpa Backend" cmd /k "cd backend && python main.py"

:: Start frontend
echo Starting frontend dev server...
start "Code Sherpa Frontend" cmd /k "cd frontend && npm run dev"

echo Waiting for services to initialize...
timeout /t 5 >nul

echo Opening browser...
start http://localhost:5173

echo ===================================
echo Code Sherpa is running!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo ===================================
