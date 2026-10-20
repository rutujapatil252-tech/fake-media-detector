#!/usr/bin/env bash
echo "========================================================"
echo "  Starting Fake Media Detector Frontend (React + Vite)"
echo "========================================================"
cd "$(dirname "$0")/frontend" || exit 1

if [ ! -d "node_modules" ]; then
    echo "Installing node dependencies..."
    npm install
fi

npm run dev
