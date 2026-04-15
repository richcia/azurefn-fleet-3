"""Pytest configuration — add repo root to sys.path for module imports."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
