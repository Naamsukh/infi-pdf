import os

def delete_all_files_in_folder(folder_path="image_blocks"):
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
    else:
        print(f"The folder '{folder_path}' does not exist.")

def save_uploaded_files(uploaded_files):
    """
    Function to save the uploaded files to the local directory
    Args:
    uploaded_files (list): List of uploaded files
    Returns:
    list: List of file paths where the files are saved
    """
    print("saving files..")
    # Define the directory path where files will be saved
    save_dir = "uploaded_files"

    # Check if the directory exists, if not, create it
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    else:
        # Delete existing files in the directory
        file_list = os.listdir(save_dir)
        print("files already exists. deleting..", file_list)
        for file_name in file_list:
            file_path = os.path.join(save_dir, file_name)
            os.remove(file_path)
    
    saved_file_paths = []
    for uploaded_file in uploaded_files:
        # Create a file path in the local directory
        file_path = os.path.join(save_dir, uploaded_file.name)
        
        # Write the uploaded file to the new file path
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        saved_file_paths.append(file_path)

    return saved_file_paths