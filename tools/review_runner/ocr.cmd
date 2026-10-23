@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ocr.ps1" %*
exit /b %ERRORLEVEL%
