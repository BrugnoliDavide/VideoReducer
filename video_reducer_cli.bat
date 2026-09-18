@echo off
cd /d "%~dp0"
python -m video_reducer %*
pause
