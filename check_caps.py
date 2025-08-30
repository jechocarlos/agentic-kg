#!/usr/bin/env python3
"""
Check relationship types to verify ALL CAPS implementation.
"""
import asyncio
import logging

from src.akg.database.neo4j_manager import Neo4jManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_relationship_types():
    """Check all relationship types in the database."""
    
    neo4j_manager = Neo4jManager()
    await neo4j_manager.initialize()
    
    try:
        # Get all relationship types
        relationship_types = await neo4j_manager.get_existing_relationship_types()
        
        logger.info(f"📊 Found {len(relationship_types)} relationship types:")
        
        # Check if all are in ALL CAPS
        all_caps_count = 0
        for rel_type in sorted(relationship_types):
            is_caps = rel_type.isupper()
            status = "✅" if is_caps else "❌"
            logger.info(f"   {status} {rel_type}")
            if is_caps:
                all_caps_count += 1
        
        logger.info(f"\n📈 ALL CAPS Summary:")
        logger.info(f"   Total relationship types: {len(relationship_types)}")
        logger.info(f"   ALL CAPS: {all_caps_count}")
        logger.info(f"   Mixed/lowercase: {len(relationship_types) - all_caps_count}")
        logger.info(f"   Percentage ALL CAPS: {(all_caps_count / len(relationship_types) * 100):.1f}%")
        
        # Show some sample relationships with their types
        async with neo4j_manager.driver.session() as session:
            result = await session.run("""
                MATCH (a)-[r]->(b)
                RETURN a.name as source, type(r) as relationship, b.name as target
                ORDER BY type(r)
                LIMIT 15
            """)
            samples = [{"source": record["source"], "relationship": record["relationship"], "target": record["target"]} async for record in result]
        
        logger.info(f"\n🔗 Sample relationships:")
        for sample in samples[:15]:
            logger.info(f"   {sample['source']} -{sample['relationship']}-> {sample['target']}")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await neo4j_manager.close()

if __name__ == "__main__":
    asyncio.run(check_relationship_types())
