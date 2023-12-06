$env:CMAKE_ARGS="-DLLAMA_CUBLAS=on"
$env:FORCE_CMAKE=1
$env:LLAMA_CUBLAS=1 

pip3 install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu121

# for troubleshooting, consider the following:
# pip cache purge
# Add `--no-cache-dir` to the pip install command
pip install llama-cpp-python --no-cache-dir --force-reinstall
