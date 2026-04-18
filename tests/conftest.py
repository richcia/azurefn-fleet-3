from pathlib import Path
import sys


repo_root_path = Path(__file__).resolve().parents[1]
repo_root = str(repo_root_path)
normalized_sys_paths = {str(Path(path).resolve()) for path in sys.path if path}
if str(repo_root_path.resolve()) not in normalized_sys_paths:
    sys.path.insert(0, repo_root)
