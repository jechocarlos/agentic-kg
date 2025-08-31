#!/usr/bin/env python3
"""
Cleanup utility to resolve existing pronoun and generic reference entities in Neo4j.
Run this after implementing coreference resolution to clean up existing data.
"""

import asyncio
import logging
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.akg.agents.coreference_resolver import CoreferenceResolver
from src.akg.database.neo4j_manager import Neo4jManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def cleanup_pronouns():
    """Clean up existing pronoun entities in Neo4j."""
    logger.info("🧹 Starting pronoun and generic reference cleanup...")
    
    # Initialize managers
    neo4j_manager = Neo4jManager()
    await neo4j_manager.initialize()
    
    coreference_resolver = CoreferenceResolver(neo4j_manager=neo4j_manager)
    
    try:
        # Run the cleanup
        await coreference_resolver.cleanup_pronoun_entities_in_neo4j('privacy_policy')
        
        logger.info("✅ Cleanup completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        raise
    
    finally:
        await neo4j_manager.close()

if __name__ == "__main__":
    print("🔧 AKG Pronoun Cleanup Utility")
    print("This will merge pronoun entities (we, you, the company, etc.) with their actual referents.")
    print("Make sure to backup your Neo4j database before running this.")
    
    confirm = input("\nDo you want to proceed? (y/N): ").strip().lower()
    if confirm in ['y', 'yes']:
        asyncio.run(cleanup_pronouns())
    else:
        print("Cleanup cancelled.")
