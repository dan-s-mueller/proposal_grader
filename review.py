#!/usr/bin/env python3
"""
Simple wrapper script for the proposal review system.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the CLI
from cli import main

if __name__ == "__main__":
    main() 