import os, shutil, requests, binascii, zipfile, time, hashlib, json, asyncio
import threading
import traceback
from . import fs_config

files_to_delete=[]

def download_single_file(filename: str, callback):
    response = requests.get(fs_config.server_url + "/file?filename=" + filename, timeout=5)
    if response.status_code == 200:

        with open(fs_config.sync_folder_location + "/" + filename, "wb+") as f:
            f.write(response.content)

        callback(response.content)
        files_to_delete.append(filename)

def download_zip_file(files_to_download: list):
    tmp_dir = "downloaded_zips/"
    os.makedirs(tmp_dir, exist_ok=True)
    response = requests.post(fs_config.server_url + "/files", data=json.dumps({"filenames": files_to_download}), timeout=5)
    if response.status_code == 200:

        local_name = tmp_dir + binascii.b2a_hex(os.urandom(8)).decode("utf-8") + ".zip"

        with open(local_name, "wb+") as f:
            f.write(response.content)

        # delete the file(s) from the server
        files_to_delete.extend(files_to_download)

        return local_name
    raise Exception(f"Download zip file failed with status: {response.status_code}, server returns: {response.content}")

def delete_files():
    global files_to_delete
    while True:
        if(files_to_delete):
            print(f"delete files: {files_to_delete}")
            try:
                del_set = files_to_delete
                response = requests.delete(fs_config.server_url + "/delete", data=json.dumps({"filenames": del_set}), timeout=5)
                if response.status_code == 200:
                    files_to_delete = list(set(files_to_delete).difference(set(del_set)))
                else:
                    print(f"File sync delete failed {response.content}")
            except Exception as e:
                print(f"File sync error occured in delete: {e}")
        time.sleep(0.5)

# gets its parameter from the return value of download_zip_file
def unzip_file(local_name: str):
    with zipfile.ZipFile(local_name, 'r') as zip_ref:
        zip_ref.extractall(fs_config.sync_folder_location)
        return zip_ref.namelist()

# takes an optional callback to process/import data
#   if one is not provided, x => x is basically a no-op
def sync(callback=lambda x: x):
    ## sorry but just one more thread bro
    t = threading.Thread(target=delete_files)
    t.setDaemon(True)
    t.start()
    #let delete file loop run
    if not os.path.exists(fs_config.sync_folder_location):
        os.makedirs(fs_config.sync_folder_location)
    while True:
        try:
            list_response = requests.get(fs_config.server_url + "/list", timeout=5)
            if list_response.status_code == 200:
                all_files = list_response.json()["files"]
                
                already_downloaded_files = []
                for file in os.listdir(fs_config.sync_folder_location):
                    already_downloaded_files.append([file, hashlib.md5(open(f'{fs_config.sync_folder_location}/{file}', "rb").read()).hexdigest()])
                files_to_download = [f for f in all_files if f not in already_downloaded_files]
                files_to_delete.extend([f[0] for f in all_files if f in already_downloaded_files])
                if len(files_to_download) == 1:
                    download_single_file(files_to_download[0][0], callback)
                elif len(files_to_download) > 1:
                    extracted_files = unzip_file(download_zip_file([f[0] for f in files_to_download]))
                    for file in extracted_files:
                        with open(fs_config.sync_folder_location + "/" + file, "rb") as f:
                            callback(f.read())
            else:
                print(f"Uh oh! request not 200: {list_response.content}")
        except Exception as e:
            print(traceback.format_exc())
        time.sleep(0.5)

if __name__ == "__main__":
    if fs_config.sync_folder_location not in os.listdir():
        os.mkdir(fs_config.sync_folder_location)
    sync()
