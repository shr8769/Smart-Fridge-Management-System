# SmartFridge — Python environment "fridge"

This workspace contains a virtual environment named `fridge` created at the project root.

Activation (PowerShell):

    # If execution policy prevents running scripts for the session, run:
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process;

    # Then activate:
    .\fridge\Scripts\Activate.ps1

Activation (cmd.exe):

    .\fridge\Scripts\activate.bat

Activation (Git Bash / WSL):

    source fridge/Scripts/activate

Install dependencies (after activation):

    pip install -r requirements.txt

Notes:
- The venv folder is `fridge` at the repository root.
- If you prefer a different environment name, delete the folder and recreate with `python -m venv <name>`.
