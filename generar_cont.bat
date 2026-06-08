@echo off
call venv\Scripts\activate
cd src\dashboard
python cont_generator.py
cd ..\..
pause