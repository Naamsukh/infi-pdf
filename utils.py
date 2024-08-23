import os

def delete_all_files_in_folder(folder_path="image_blocks"):
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
    else:
        print(f"The folder '{folder_path}' does not exist.")