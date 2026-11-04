@echo off
title Google Maps Scraper Web Dashboard
echo ===================================================
echo Starting Google Maps Scraper Web Server...
echo URL: http://127.0.0.1:8000
echo Press Ctrl+C in this terminal to stop the server.
echo ===================================================

start "" http://127.0.0.1:8000
python -m uvicorn web.app:app --host 127.0.0.1 --port 8000
pause
