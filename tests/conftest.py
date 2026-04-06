import sys
import os

# Allow root-level module imports (e.g. trapi_client) from the tests directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
