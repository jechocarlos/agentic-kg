#!/usr/bin/env python3
"""
Script to clear Neo4j database and reprocess documents with proper relationship types.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from akg.config import AKGConfig
from akg.database.neo4j_manager import Neo4jManager


async def clear_and_reprocess():
    """Clear the Neo4j database and reprocess documents."""
    neo4j_manager = Neo4jManager()
    
    try:
        # Initialize connection
        await neo4j_manager.initialize()
        print("✅ Connected to Neo4j")
        
        # Clear all data using the manager method
        success = await neo4j_manager.clear_all_data()
        
        if success:
            print("✅ Database cleared successfully!")
            print("\n🚀 Now run: python run.py")
            print("   This will reprocess documents with proper relationship types.")
        else:
            print("❌ Failed to clear database")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await neo4j_manager.close()

if __name__ == "__main__":
    asyncio.run(clear_and_reprocess())
