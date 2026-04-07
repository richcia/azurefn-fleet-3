import sys
import os

# Allow root-level module imports (e.g. trapi_client) when running pytest
# from within the tests/ directory or from the repo root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
