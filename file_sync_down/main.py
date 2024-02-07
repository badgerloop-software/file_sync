import config, os, shutil, requests, binascii, zipfile, time, hashlib

def download_single_file(filename: str):
    response = requests.get(config.server_url + "/file?filename=" + filename)
    assert response.status_code == 200

    with open(config.sync_folder_location + "/" + filename, "wb+") as f:
        f.write(response.content)

    # delete the file from the server
    delete_files([filename])

def download_zip_file(files_to_download: list):
    tmp_dir = "downloaded_zips/"
    os.makedirs(tmp_dir, exist_ok=True)
    comma_separated_list = ','.join(files_to_download)
    response = requests.get(config.server_url + "/files?filenames=" + comma_separated_list)
    assert response.status_code == 200

    local_name = tmp_dir + binascii.b2a_hex(os.urandom(8)).decode("utf-8") + ".zip"

    with open(local_name, "wb+") as f:
        f.write(response.content)

    # delete the file(s) from the server
    delete_files(files_to_download)

    return local_name

def delete_files(files_to_delete: list):
    comma_separated_list = ','.join(files_to_delete)
    response = requests.delete(config.server_url + "/delete?filenames=" + comma_separated_list)
    assert response.status_code == 200

# gets its parameter from the return value of download_zip_file
def unzip_file(local_name: str):
    with zipfile.ZipFile(local_name, 'r') as zip_ref:
        zip_ref.extractall(config.sync_folder_location)

def sync():
    while True:
        list_response = requests.get(config.server_url + "/list")
        assert list_response.status_code == 200
        all_files = list_response.json()["files"]
        
        already_downloaded_files = []
        for file in os.listdir(config.sync_folder_location):
            already_downloaded_files.append([file, hashlib.md5(open(f'{config.sync_folder_location}/{file}', "rb").read()).hexdigest()])
        print("already downloaded files:", already_downloaded_files)
        files_to_download = [f for f in all_files if f not in already_downloaded_files]
        print("files to download:", files_to_download)

        if len(files_to_download) == 1:
            download_single_file(files_to_download[0][0])
        elif len(files_to_download) > 1:
            unzip_file(download_zip_file([f[0] for f in files_to_download]))
        # otherwise we have nothing to do

        time.sleep(0.5)

if __name__ == "__main__":
    if config.sync_folder_location not in os.listdir():
        os.mkdir(config.sync_folder_location)
    sync()
