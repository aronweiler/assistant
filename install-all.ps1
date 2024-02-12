# If the python environment does not exist, create it
if (-not (Test-Path -Path "assistant_venv")) {
    python -m venv assistant_venv
}

Invoke-Expression -Command .\assistant_venv\Scripts\activate
python.exe -m pip install --upgrade pip

pip install -r requirements-ui.txt
pip install -r requirements-services.txt