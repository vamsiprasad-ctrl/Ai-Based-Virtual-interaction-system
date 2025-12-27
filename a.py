"""
Placeholder file 'a.py' - Simple utility script
Can be used for quick testing or temporary scripts
"""

import sys
from datetime import datetime

def print_info():
    """Print system information"""
    print("=" * 60)
    print("SYSTEM INFORMATION")
    print("=" * 60)
    print(f"Python Version: {sys.version}")
    print(f"Platform: {sys.platform}")
    print(f"Current Time: {datetime.now()}")
    print("=" * 60)

if __name__ == "__main__":
    print_info()
