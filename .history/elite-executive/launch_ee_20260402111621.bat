@echo off
@REM Update the path below to point to the location of your content tools folder
cd /d "C:\Users\lordb\Desktop\content tools"
call .venv\Scripts\activate.bat
python "elite-executive\ee_gui.py"