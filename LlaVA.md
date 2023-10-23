
## Clone llama.cpp
`git clone https://github.com/ggerganov/llama.cpp.git`

## Build llama.cpp with GPU enabled
From the llama.cpp dir, run the following:
- `mkdir build`
- `cd build`
- `cmake .. -DLLAMA_CUBLAS=ON`
- `cmake --build . --config Release`

# Run image inference directly
From the Release directory created when building:
- `llava.exe -m H:\LLM\llava-v1.5-7b\ggml-model-q5_k.gguf --mmproj H:\LLM\llava-v1.5-7b\mmproj-model-f16.gguf --temp 0.1 -ngl 50 -p "<prompt text>" --image "<image path>"`

Make sure to replace the model names/paths with ones on your system.

## Run image inference within Jarvis
- Set the `LLAVA_PATH` environment variable to the location of llava.exe
- Set the `LLAVA_MODEL` environment variable (e.g. "H:\LLM\llava-v1.5-7b\ggml-model-q5_k.gguf")
- Set the `LLAVA_MMPROJ` environment variable (e.g. "H:\LLM\llava-v1.5-7b\mmproj-model-f16.gguf")
- Set the `LLAVA_TEMP` environment variable (e.g. "0.1")
- Set the `LLAVA_GPU_LAYERS` environment variable (e.g. "50")
- Make sure you enable the image_query tool in Jarvis
- Load images in files/settings (You don't need to select a file-type for images, just upload them)
- Query Jarvis about any loaded `Image` classified files

