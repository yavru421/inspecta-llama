@echo off
REM Create venv if it does not exist
if not exist "venv\Scripts\activate.bat" (
    python -m venv venv
)

REM Activate virtual environment
call "venv\Scripts\activate.bat"

REM Install requirements
pip install -r requirements.txt

REM Load API key from .env file
for /f "tokens=2 delims==" %%A in ('findstr "LLAMA_API_KEY=" .env') do set LLAMA_API_KEY=%%A

REM Run the app (GUI mode by default, or drill down if specified)
if "%1"=="drilldown" (
    python cumulative_app.py --drilldown
) else (
    python cumulative_app.py --gui
)

pause

import tkinter as tk

def run_gui():
    root = tk.Tk()
    root.title("Inspectallama GUI")
    # ... add widgets ...
    root.mainloop()

if __name__ == "__main__":
    run_gui()