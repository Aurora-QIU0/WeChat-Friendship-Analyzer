@echo off
cd /d "%~dp0"
echo Open http://127.0.0.1:8765 after the server starts.
python -B -X utf8 scripts/local_app.py
pause
