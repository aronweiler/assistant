# If the python environment does not exist, create it
if (-not (Test-Path -Path "assistant_ui_venv")) {
    python -m venv assistant_ui_venv
}

Invoke-Expression -Command .\assistant_ui_venv\Scripts\activate
python.exe -m pip install --upgrade pip

pip install -r requirements-ui.txt