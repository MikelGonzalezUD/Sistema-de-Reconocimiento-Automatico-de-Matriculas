@echo off
call venv\Scripts\activate
cd src\database
python db_tests.py
cd ..\..
pause
