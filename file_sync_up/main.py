import os, config, requests, hashlib, shutil, tempfile
import time

sync_folder_location = str(tempfile.gettempdir()) + "/driver-io-file-sync"

# compare files with server
# if file exist on server, delete file locally
# if file doesn't exist on server, upload file to server

def upload_file(endpoint: str, filename: str, file_dir: str = ""):
    with open(os.path.join(file_dir, filename), "rb") as f:
        file_content = f.read()
    md5 = hashlib.md5(file_content).hexdigest()
    print(md5)
    file = {'file': (filename, file_content, 'multipart/form-data')}
    response = requests.post(config.server_url + endpoint + f'md5={md5}', files=file)
    print(response.json())

def zip_file(files) -> str:
    tmp_dir = "temp_files"
    os.makedirs(tmp_dir, exist_ok=True)
    # Copy each file from the "Files" directory to the temporary directory
    for filename in files:
        source_path = os.path.join(config.sync_folder_location, filename.strip())
        dest_path = os.path.join(tmp_dir, filename.strip())
        shutil.copy2(source_path, dest_path)
    # Create a zip archive of the files in the temporary directory
    shutil.make_archive(tmp_dir, 'zip', tmp_dir)
    # Get the path to the generated zip file
    shutil.rmtree(tmp_dir)
    return tmp_dir + ".zip"

def sync():
    while(True):
        # compare files with server
        files = os.listdir(sync_folder_location)

        try:
            response = requests.post(config.server_url + "/compare_files", json={"files": files}, timeout=5)
        except Exception as e:
            print("Error Connecting to file sync Server")
            continue

        missing_files = response.json()["missing"]
        print(missing_files)
        if len(missing_files) == 1:
            # upload file to server
            upload_file("/uploadfile?", missing_files[0], config.sync_folder_location)
        elif len(missing_files) > 1:
            # upload zip file to server
            zipfile = zip_file(missing_files)
            upload_file("/uploadzip?", zipfile)
            os.remove(zipfile)
        # remove file locally
        for file in files:
            if file not in missing_files:
                os.remove(os.path.join(config.sync_folder_location, file))
        time.sleep(0.5)


if __name__ == "__main__":
    sync()
            
        
    