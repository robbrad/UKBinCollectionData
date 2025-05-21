"""
Configure pytest for the UK Bin Collection tests.
This helps resolve import issues when running tests.
"""

import os
import sys
from pathlib import Path

# Add the project root to sys.path to help with imports
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))
