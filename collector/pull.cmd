@echo off
setlocal
cd /d "%~dp0"
if not exist "cache" mkdir "cache"
echo ===== %DATE% %TIME% =====>> "cache\pull.log"
py -3 -m collector pull >> "cache\pull.log" 2>&1
exit /b %ERRORLEVEL%
