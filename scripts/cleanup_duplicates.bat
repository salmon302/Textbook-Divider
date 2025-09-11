@echo off
REM Wrapper to run cleanup_duplicates.ps1 from the repo root
SETLOCAL
SET ROOT=%~dp0..\
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0cleanup_duplicates.ps1" -Root "%ROOT%" %*
ENDLOCAL
