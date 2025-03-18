# tests/__init__.py
"""
Test suite for glacier-rsync.
Contains tests for both original functionality and new features (encryption and progress bars).
"""

import os
import sys

# Add the parent directory to the path so we can import glacier_rsync
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
 
