#!/usr/bin/env python3
"""
Startup script for the Fantasy Basketball Backend
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Now we can import and run
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=3002,
        reload=True,
        reload_dirs=[project_root]
    )