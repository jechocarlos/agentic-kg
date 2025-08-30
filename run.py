#!/usr/bin/env python3
"""
Simple CLI runner for AKG system.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from akg.main import main

if __name__ == "__main__":
    asyncio.run(main())
