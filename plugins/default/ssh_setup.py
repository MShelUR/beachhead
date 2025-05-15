import os
import stat

def create_ssh_folder(path: str):
    try:
        os.makedirs(path, mode=0o700)
        print(f"Successfully created directory {path}")
    except FileExistsError:
        return FileExistsError(f"Directory {path} already exists.")
    except OSError as error:
        return OSError(f"Error creating directory {path}: {error}")
    
def main() -> int:
    ssh_folder_path = os.path.join(os.path.expanduser("~"), ".ssh")
    create_ssh_folder(ssh_folder_path)
    