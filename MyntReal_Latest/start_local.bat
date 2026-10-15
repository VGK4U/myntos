@echo off
echo Starting MyntReal Local Servers...

:: Start Backend in a new window
echo Starting Backend (FastAPI)...
start "MyntReal Backend" cmd /k "cd backend && set PYTHONIOENCODING=utf-8 && set ALLOW_PROD_DB_ACCESS=1 && python -m uvicorn app.main:app --port 8000 --reload"

:: Start Frontend in a new window
echo Starting Frontend (Node.js)...
start "MyntReal Frontend" cmd /k "cd frontend && set PORT=5000 && node server.js"

:: Start WhatsApp Bot in a new window
echo Starting WhatsApp Bot (Node.js)...
start "MyntReal WhatsApp Bot" cmd /k "cd backend\whatsapp-group-bot && node server.js"

echo All servers are starting up!
echo Once they are ready, open your browser and go to:
echo - Frontend: http://localhost:5000
echo - Backend API Docs: http://localhost:8000/docs
echo - WhatsApp Bot QR: http://localhost:5002/qr
echo.
