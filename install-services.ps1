# If the python environment does not exist, create it
if (-not (Test-Path -Path "assistant_services_venv")) {
    python -m venv assistant_services_venv
}

Invoke-Expression -Command .\assistant_services_venv\Scripts\activate
python.exe -m pip install --upgrade pip

pip install -r src/services/requirements.txt