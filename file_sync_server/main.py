import copy
from fastapi import FastAPI, UploadFile, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
import shutil, hashlib
import os
from typing import List

app = FastAPI()

@app.get("/files")
async def download_files(filenames: str):
    # Split the comma-separated filenames into a list
    filename_list = filenames.split(',')
    # Create a temporary directory to store the files before zipping
    tmp_dir = "temp_files"
    os.makedirs(tmp_dir, exist_ok=True)

    # Copy each file from the "Files" directory to the temporary directory
    for filename in filename_list:
        source_path = os.path.join("Files", filename.strip())
        dest_path = os.path.join(tmp_dir, filename.strip())
        shutil.copy2(source_path, dest_path)

    # Create a zip archive of the files in the temporary directory
    shutil.make_archive(tmp_dir, 'zip', tmp_dir)

    # Get the path to the generated zip file
    zip_file_path = tmp_dir + ".zip"

    # Delete the temporary directory
    shutil.rmtree(tmp_dir)

    # Return the zip file as a response
    return FileResponse(zip_file_path, media_type="application/zip", filename='Files.zip')

@app.get("/file")
async def read_file(filename: str = Query(..., description="Name of the file to download")):
    file_path = f"Files/{filename}"  # Update the path to your local directory
    return FileResponse(file_path, media_type="application/octet-stream", filename=filename)

class Item(BaseModel):
    files: list

@app.post("/compare_files")
async def compare_files(files: Item):
    """Uploads a list of file names and returns a list of files not found in the 'Files' folder on the server side"""
    local_files = set(os.listdir('Files'))
    not_found = [file for file in files.files if file not in local_files]
    return {"missing": not_found}

@app.get("/list")
async def list_files():
    """returns a list of files in the Files folder on server side"""
    return {"files": os.listdir('Files')}

@app.post("/uploadfile")
async def create_upload_file(file: UploadFile, md5: str):
    f_data = file.file.read()
    if hashlib.md5(f_data).hexdigest() != md5:
        return {"error": "md5 checksum failed"}
    with open(f'Files/{file.filename}', "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"filename": file.filename}

@app.post("/uploadzip")
async def upload_zip(file: UploadFile, md5: str):
    f_data = file.file.read()
    if hashlib.md5(f_data).hexdigest() != md5:
        return {"error": "md5 checksum failed"}
    with open(f'{file.filename}', "wb") as f:
        f.write(f_data)
    shutil.unpack_archive(file.filename, 'Files')
    os.remove(file.filename)
    return {"filename": file.filename}


if __name__ == '__main__':
    import uvicorn
    if "Files" not in os.listdir():
        os.mkdir("Files")
    uvicorn.run(app, host='0.0.0.0', port=8000)
