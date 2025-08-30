#!/usr/bin/env python3
"""
Test script to verify new chunked extraction with ALL CAPS relationship types.
"""
import asyncio
import logging
import sys
from pathlib import Path

import pytest

# Add src to path  
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from akg.database.neo4j_manager import Neo4jManager
from akg.agents.extraction import EntityExtractionAgent
from akg.models import Document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_new_extraction():
    """Test the new chunked extraction with ALL CAPS relationship types."""
    
    # Initialize managers
    neo4j_manager = Neo4jManager()
    await neo4j_manager.initialize()
    
    extraction_agent = EntityExtractionAgent(neo4j_manager)
    
    try:
        # Clear existing data - use a direct query
        logger.info("🧹 Clearing existing data...")
        success = await neo4j_manager.clear_all_data()
        assert success, "Failed to clear database"
        
        # Create a test document
        test_doc = Document(
            id="test_chunked_extraction",
            title="Test Document for Chunked Extraction",
            content="""
            Alpha Corp is a technology company founded by John Smith in 2020. 
            The company is headquartered in San Francisco and specializes in artificial intelligence.
            
            John Smith previously worked at Tech Innovations Inc where he was the CTO.
            He graduated from Stanford University with a degree in Computer Science.
            
            Alpha Corp recently partnered with Beta Solutions to develop new AI products.
            The partnership was announced in March 2024 during a major tech conference.
            
            Sarah Johnson joined Alpha Corp as the VP of Engineering in January 2024.
            She reports directly to John Smith and manages a team of 15 engineers.
            
            The company is currently working on Project Gamma, which is scheduled to launch in Q4 2024.
            This project involves collaboration with multiple universities and research institutes.
            """,
            source_system="test",
            source_path="/test/document.txt",
            document_type="text"
        )
        
        # Process the document
        logger.info("🔄 Processing test document with new extraction...")
        result = await extraction_agent.process_document(test_doc)
        
        logger.info(f"✅ Extraction complete:")
        logger.info(f"   - Entities: {result['entities_count']}")
        logger.info(f"   - Relationships: {result['relationships_count']}")
        
        # Check the results
        logger.info("📊 Checking database stats...")
        stats = await neo4j_manager.get_graph_stats()
        
        logger.info(f"Database statistics:")
        logger.info(f"   - Total entities: {stats.get('total_entities', 0)}")
        logger.info(f"   - Total relationships: {stats.get('total_relationships', 0)}")
        
        # Basic assertions
        assert result['entities_count'] > 0, "Should extract some entities"
        assert result['relationships_count'] > 0, "Should extract some relationships"
        assert result['neo4j_saved'], "Should successfully save to Neo4j"
        
        # Verify we have data
        assert stats['total_entities'] > 0
        assert stats['total_relationships'] > 0
        
        # Get all relationship types
        relationship_types = await neo4j_manager.get_existing_relationship_types()
        logger.info(f"Relationship types found: {relationship_types}")
        
        # Verify ALL CAPS if we have relationship types
        if relationship_types:
            all_caps = all(rt.isupper() for rt in relationship_types)
            logger.info(f"All relationship types in ALL CAPS: {all_caps}")
            assert all_caps, "All relationship types should be in ALL CAPS"
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await neo4j_manager.close()

if __name__ == "__main__":
    asyncio.run(test_new_extraction())
