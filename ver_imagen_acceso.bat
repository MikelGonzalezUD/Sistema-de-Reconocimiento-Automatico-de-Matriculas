@echo off
call venv\Scripts\activate
cd src\database
python imagen_db.py
cd ..\..
pause
