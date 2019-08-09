@echo off
setlocal
:: This is required with cygwin only.
PATH=%~dp0;%PATH%
set PYTHONDONTWRITEBYTECODE=1
call "%USERPROFILE%\AppData\Local\Programs\Python\Python37\python.exe" "%~dp0crbuild.py" %*
