import os
import shutil
import pathlib

def remove_venvs(base_dir):
    base_path = pathlib.Path(base_dir)
    print(f"Scanning for 'venv' or '.venv' directories in {base_path}...")
    
    count = 0
    # Walk through the directory tree
    for root, dirs, files in os.walk(base_dir):
        # Ignore specific folders to speed up the process
        dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', '__pycache__')]
        
        for d in list(dirs):
            if d in ('venv', '.venv'):
                venv_path = os.path.join(root, d)
                print(f"Removing {venv_path}...")
                try:
                    # Remove the virtual environment directory
                    shutil.rmtree(venv_path)
                    print(f"  -> Successfully removed")
                    count += 1
                    # Remove from dirs so os.walk doesn't try to traverse into it
                    dirs.remove(d)
                except Exception as e:
                    print(f"  -> Error removing {venv_path}: {e}")

    print(f"\nDone! Removed {count} virtual environment(s).")

if __name__ == "__main__":
    # Get the parent directory of 'scripts', which should be 'vora_fastapi'
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # Execute the cleanup
    remove_venvs(project_root)
