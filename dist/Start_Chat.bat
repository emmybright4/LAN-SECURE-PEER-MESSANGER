@echo off
title SecureLocal Chat Launcher
echo ========================================
echo    SECURELOCAL CHAT LAUNCHER
echo ========================================
echo.

echo [1/3] Starting SecureLocal Chat...
start "" "%~dp0SecureLocalChat.exe"

echo [2/3] Waiting for app to initialize...
timeout /t 3 >nul

echo [3/3] Opening browser...
start http://localhost:5000

echo.
echo App started successfully!
echo The app is running in the background
echo Browser should open automatically
echo.
echo Press any key to close this window...
pause >nul
exit