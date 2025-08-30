#!/usr/bin/env python3
"""
Simple script to check relationships in Neo4j database.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from akg.config import AKGConfig
from akg.database.neo4j_manager import Neo4jManager


async def check_relationships():
    """Check what relationships exist in the Neo4j database."""
    neo4j_manager = Neo4jManager()
    
    try:
        # Initialize connection
        await neo4j_manager.initialize()
        print("✅ Connected to Neo4j")
        
        # Get overall stats
        stats = await neo4j_manager.get_graph_stats()
        print(f"\n📊 Database Statistics:")
        print(f"  - Total entities: {stats['total_entities']}")
        print(f"  - Total relationships: {stats['total_relationships']}")
        print(f"  - Total documents: {stats['total_documents']}")
        
        # Check relationship types
        rel_types = await neo4j_manager.get_existing_relationship_types()
        print(f"\n🔗 Relationship Types ({len(rel_types)}):")
        for rel_type in sorted(rel_types):
            print(f"  - {rel_type}")
        
        # Sample some relationships with more detail
        async with neo4j_manager.driver.session() as session:
            query = """
            MATCH (a)-[r]->(b)
            RETURN type(r) as relationship_type, 
                   r.type as stored_type,
                   a.name as from_entity, 
                   b.name as to_entity,
                   r.confidence as confidence
            LIMIT 15
            """
            result = await session.run(query)
            
            print(f"\n📋 Sample Relationships (with details):")
            count = 0
            async for record in result:
                count += 1
                stored_type = record['stored_type'] or 'N/A'
                confidence = record['confidence'] or 'N/A'
                print(f"  {count}. {record['from_entity']} --[{record['relationship_type']}]-- {record['to_entity']}")
                print(f"      └─ Stored type: {stored_type}, Confidence: {confidence}")
        
        # Check for isolated nodes
        async with neo4j_manager.driver.session() as session:
            query = """
            MATCH (n:Entity)
            WHERE NOT (n)--()
            RETURN n.name as isolated_entity, n.type as entity_type
            LIMIT 10
            """
            result = await session.run(query)
            
            print(f"\n🏝️ Isolated Nodes (no relationships):")
            count = 0
            async for record in result:
                count += 1
                print(f"  {count}. {record['isolated_entity']} ({record['entity_type']})")
            
            if count == 0:
                print("  ✅ No isolated nodes found!")
        
        # Check entities with only document relationships
        async with neo4j_manager.driver.session() as session:
            query = """
            MATCH (e:Entity)
            WHERE NOT (e)-[:RELATES_TO]-()
            AND (e)-[:MENTIONED_IN]-()
            RETURN e.name as entity_name, e.type as entity_type
            LIMIT 10
            """
            result = await session.run(query)
            
            print(f"\n📄 Entities with only document relationships:")
            count = 0
            async for record in result:
                count += 1
                print(f"  {count}. {record['entity_name']} ({record['entity_type']})")
            
            if count == 0:
                print("  ✅ All entities have inter-entity relationships!")
        
        # Count relationships by type
        async with neo4j_manager.driver.session() as session:
            query = """
            MATCH ()-[r]->()
            RETURN type(r) as relationship_type, count(r) as count
            ORDER BY count DESC
            """
            result = await session.run(query)
            
            print(f"\n📈 Relationship Counts by Type:")
            async for record in result:
                print(f"  - {record['relationship_type']}: {record['count']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await neo4j_manager.close()

if __name__ == "__main__":
    asyncio.run(check_relationships())
