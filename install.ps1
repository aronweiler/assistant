python -m venv assistant_venv
Invoke-Expression -Command .\assistant_venv\Scripts\activate
python.exe -m pip install --upgrade pip
# Comment the following lines (through the torch install) if you don't have a GPU that you want to use with llamacpp
$env:CMAKE_ARGS="-DLLAMA_CUBLAS=on"      
$env:FORCE_CMAKE=1
$env:LLAMA_CUBLAS=1 
pip3 install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu121
pip cache purge
pip --no-cache-dir install -r requirements.txt