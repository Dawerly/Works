@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
  if errorlevel 1 goto :failed
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :failed
.venv\Scripts\python.exe server.py
pause
exit /b
:failed
echo Не вдалося підготувати Python. Перевірте Python 3.9+ та інтернет.
pause
exit /b 1
