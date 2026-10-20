@echo off
echo ========================================================
echo   Starting Fake Media Detector Backend (FastAPI)
echo ========================================================
cd backend
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
    python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
) else (
    echo Error: Virtual environment .venv was not found in backend/
    echo Please create it first:
    echo   cd backend
    echo   python -m venv .venv
    echo   .\.venv\Scripts\pip install -r requirements.txt
    pause
)
