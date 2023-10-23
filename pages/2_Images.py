import os
import re
import subprocess
import streamlit as st
from PIL import Image
from io import StringIO

LLAVA_CMD = '{llava_path} -m {llava_model} --mmproj {llava_mmproj} --temp {llava_temp} -ngl {llava_gpu_layers} -p "{prompt}" --image "{image_path}"'



def extract_text(input):
    pattern = r"prompt: '(.+?)'\n\n(.*?)\n\nmain:"

    match = re.search(pattern=pattern, string=input, flags=re.DOTALL)

    if match:
        extracted_text = match.group(1).strip()
        return extracted_text
    else:
        return input



def query_image(file_name: int, query: str) -> str:
    llava_path = os.environ.get("LLAVA_PATH", None)
    llava_model = os.environ.get("LLAVA_MODEL", None)
    llava_mmproj = os.environ.get("LLAVA_MMPROJ", None)
    llava_temp = float(os.environ.get("LLAVA_TEMP", 0.1))
    llava_gpu_layers = int(os.environ.get("LLAVA_GPU_LAYERS", 50))

    command = LLAVA_CMD.format(
        llava_path=llava_path,
        prompt=query,
        image_path=file_name,
        llava_model=llava_model,
        llava_mmproj=llava_mmproj,
        llava_temp=llava_temp,
        llava_gpu_layers=llava_gpu_layers,
    )

    # Execute the command
    result = subprocess.run(command, shell=True, capture_output=True)

    return extract_text(input=result.stdout.decode("utf-8"))


with st.sidebar.container():
    uploaded_file = st.file_uploader("Choose a file")
    if uploaded_file is not None:
        # To read file as bytes:
        bytes_data = uploaded_file.getvalue()

        # Make sure the directory exists
        if not os.path.exists("temp"):
            os.makedirs("temp")

        # Write the file out to the temp directory
        with open("temp/file.jpg", "wb") as outfile:
            outfile.write(bytes_data)

col1, col2 = st.columns(2)

# Does the last-uploaded file exist?
if os.path.isfile("temp/file.jpg"):
    image = Image.open("temp/file.jpg")
    col1.image(image, caption="Uploaded file", use_column_width=True)

    query = st.chat_input("Enter a query for the image")
    
    if query is not None:
        result = query_image("temp/file.jpg", query)
        col2.write(result)
        
