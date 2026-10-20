@echo off
echo ========================================================
echo   Starting Fake Media Detector Frontend (React + Vite)
echo ========================================================
cd frontend
if not exist node_modules (
    echo Installing node dependencies...
    call npm.cmd install
)
call npm.cmd run dev
