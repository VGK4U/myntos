@echo off
echo Starting MyntReal Local Servers...

:: Start Backend in a new window
echo Starting Backend (FastAPI)...
start "MyntReal Backend" cmd /k "cd backend && set PYTHONIOENCODING=utf-8 && python -m uvicorn app.main:app --port 8000 --reload"

:: Start Frontend in a new window
echo Starting Frontend (Node.js)...
start "MyntReal Frontend" cmd /k "cd frontend && set PORT=5000 && node server.js"

echo Both servers are starting up!
echo Once they are ready, open your browser and go to:
echo http://localhost:5000
echo.
pause
