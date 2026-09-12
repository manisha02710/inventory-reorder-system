@echo off
title Inventory Reorder Prediction Web App
cd /d "%~dp0"
echo =================================================================
echo  Launching Inventory Reorder Prediction Web App (FastAPI + UI)
echo =================================================================
echo.
.venv\Scripts\python.exe run.py
pause
