@echo off
cd /d "%~dp0backend"
set PYTHONIOENCODING=utf-8
set ALLOW_PROD_DB_ACCESS=1
python -m uvicorn app.main:app --port 8000
