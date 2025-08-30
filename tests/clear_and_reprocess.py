#!/usr/bin/env python3
"""
Script to clear Neo4j database and reprocess documents with proper relationship types.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from akg.config import AKGConfig
from akg.database.neo4j_manager import Neo4jManager


async def clear_and_reprocess():
    """Clear the Neo4j database and reprocess documents."""
    config = AKGConfig()
    neo4j_manager = Neo4jManager(
        uri=config.neo4j_uri,
        username=config.neo4j_username,
        password=config.neo4j_password
    )
    
    try:
        # Initialize connection
        await neo4j_manager.initialize()
        print("✅ Connected to Neo4j")
        
        # Clear all data
        async with neo4j_manager.driver.session() as session:
            print("🗑️ Clearing all relationships...")
            await session.run("MATCH ()-[r]-() DELETE r")
            
            print("🗑️ Clearing all entities...")
            await session.run("MATCH (n:Entity) DELETE n")
            
            print("🗑️ Clearing all documents...")
            await session.run("MATCH (n:Document) DELETE n")
            
        print("✅ Database cleared successfully!")
        print("\n🚀 Now run: python run.py")
        print("   This will reprocess documents with proper relationship types.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await neo4j_manager.close()

if __name__ == "__main__":
    asyncio.run(clear_and_reprocess())
