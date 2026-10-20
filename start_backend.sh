#!/usr/bin/env bash
echo "========================================================"
echo "  Starting Fake Media Detector Backend (FastAPI)"
echo "========================================================"
cd "$(dirname "$0")/backend" || exit 1

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
else
    echo "Error: Virtual environment .venv not found in backend/"
    echo "Please create it: cd backend && python -m venv .venv && pip install -r requirements.txt"
    exit 1
fi

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
