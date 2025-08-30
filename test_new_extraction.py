#!/usr/bin/env python3
"""
Test script to verify new chunked extraction with ALL CAPS relationship types.
"""
import asyncio
import logging
from pathlib import Path

from src.akg.database.neo4j_manager import Neo4jManager
from src.akg.agents.extraction import EntityExtractionAgent
from src.akg.models import Document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_new_extraction():
    """Test the new chunked extraction with ALL CAPS relationship types."""
    
    # Initialize managers
    neo4j_manager = Neo4jManager()
    await neo4j_manager.initialize()
    
    extraction_agent = EntityExtractionAgent(neo4j_manager)
    
    try:
        # Clear existing data - use a direct query
        logger.info("🧹 Clearing existing data...")
        async with neo4j_manager.driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
        
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
        
        # Get all relationship types
        async with neo4j_manager.driver.session() as session:
            result = await session.run("""
                MATCH ()-[r]->()
                RETURN DISTINCT type(r) as relationship_type
                ORDER BY relationship_type
            """)
            relationship_types = [record["relationship_type"] async for record in result]
        
        logger.info(f"Relationship types found: {relationship_types}")
        
        # Verify ALL CAPS
        all_caps = all(rt.isupper() for rt in relationship_types)
        logger.info(f"All relationship types in ALL CAPS: {all_caps}")
        
        # Show some sample relationships
        async with neo4j_manager.driver.session() as session:
            result = await session.run("""
                MATCH (a)-[r]->(b)
                RETURN a.name as source, type(r) as relationship, b.name as target
                LIMIT 10
            """)
            samples = [{"source": record["source"], "relationship": record["relationship"], "target": record["target"]} async for record in result]
        
        logger.info("Sample relationships:")
        for sample in samples:
            logger.info(f"   {sample['source']} -{sample['relationship']}-> {sample['target']}")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await neo4j_manager.close()

if __name__ == "__main__":
    asyncio.run(test_new_extraction())
