@echo off
REM Check if the virtual environment folder already exists
IF NOT EXIST ".venv" (
    REM Create the virtual environment
    python -m venv .venv
)

REM Activate the virtual environment
call .venv\Scripts\activate

REM Upgrade pip
python -m pip install --upgrade pip

REM Install dependencies from requirements.txt
pip install -r requirements.txt