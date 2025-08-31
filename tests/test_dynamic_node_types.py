#!/usr/bin/env python3
"""
Test script to compare dynamic vs static node types in the AKG system.

This script demonstrates the difference between:
1. Old approach: All nodes have :Entity label, type stored as property
2. New approach: Nodes have :Entity + specific type labels (e.g., :Entity:PERSON, :Entity:API)
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

# Add the parent directory to the path to access src
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from akg.agents.extraction import EntityExtractionAgent
from akg.database.neo4j_manager import Neo4jManager
from akg.models import Document, Entity


async def demo_node_type_comparison():
    """Demonstrate the difference between static and dynamic node types."""
    
    print("🧪 AKG NODE TYPE COMPARISON DEMO")
    print("=" * 60)
    
    # Initialize Neo4j manager
    neo4j = Neo4jManager()
    await neo4j.initialize()
    
    print("\n📊 CURRENT GRAPH STATE:")
    stats = await neo4j.get_graph_stats()
    print(f"  Total Entities: {stats['total_entities']}")
    print(f"  Total Relationships: {stats['total_relationships']}")
    print(f"  Total Documents: {stats['total_documents']}")
    
    # Get sample of existing nodes (old style)
    print(f"\n📋 EXISTING NODES (Old Style - :Entity label only):")
    existing_nodes = await neo4j.get_nodes_with_labels()
    
    for i, node in enumerate(existing_nodes[:5]):
        if not node['id'].startswith('test-'):
            labels_str = ', '.join(node['node_labels'])
            print(f"  {i+1}. {node['name'][:30]:30} | Labels: [{labels_str}] | Type: {node['entity_type']}")
    
    # Create new nodes with dynamic labels
    print(f"\n🆕 CREATING DYNAMIC-LABELED NODES:")
    
    test_entities = [
        ('demo-person', 'Alice Developer', 'PERSON', {'role': 'senior_developer', 'team': 'backend'}),
        ('demo-api', 'User Management API', 'API', {'version': 'v2.1', 'status': 'production'}),
        ('demo-database', 'Customer Database', 'DATABASE', {'type': 'postgresql', 'environment': 'prod'}),
        ('demo-service', 'Authentication Service', 'MICROSERVICE', {'language': 'python', 'framework': 'fastapi'}),
        ('demo-document', 'API Specification', 'DOCUMENT', {'format': 'openapi', 'version': '3.0'}),
        ('demo-algorithm', 'Recommendation Engine', 'ALGORITHM', {'type': 'ml', 'framework': 'tensorflow'}),
    ]
    
    for entity_id, name, entity_type, props in test_entities:
        success = await neo4j.create_entity(entity_id, name, entity_type, 'demo-comparison', props, 0.95)
        if success:
            sanitized_type = neo4j._sanitize_label(entity_type)
            print(f"  ✅ {name:30} → :Entity:{sanitized_type}")
        else:
            print(f"  ❌ Failed to create {name}")
    
    # Show the new dynamic-labeled nodes
    print(f"\n🆕 NEW NODES (Dynamic Style - :Entity + Specific Labels):")
    dynamic_nodes = await neo4j.get_nodes_with_labels('demo-')
    
    for i, node in enumerate(dynamic_nodes):
        labels_str = ', '.join(node['node_labels'])
        print(f"  {i+1}. {node['name'][:30]:30} | Labels: [{labels_str}] | Type: {node['entity_type']}")
    
    # Demonstrate query capabilities
    print(f"\n🔍 QUERY CAPABILITIES COMPARISON:")
    
    # Query by specific label (only works with new style)
    print(f"\n1. Query all PERSON nodes using specific label:")
    person_nodes = await neo4j.get_nodes_with_labels()
    person_count = len([n for n in person_nodes if 'PERSON' in n['node_labels']])
    print(f"   Found {person_count} nodes with :PERSON label")
    
    # Query by type property (works with both old and new)
    print(f"\n2. Query all PERSON nodes using type property:")
    person_entities = await neo4j.search_entities('', 'PERSON')
    print(f"   Found {len(person_entities)} nodes with type='PERSON'")
    
    # Show domain-specific grouping
    print(f"\n🏷️ DOMAIN-SPECIFIC NODE GROUPING:")
    
    all_nodes = await neo4j.get_nodes_with_labels()
    type_counts = {}
    
    for node in all_nodes:
        entity_type = node['entity_type'] or 'UNKNOWN'
        type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
    
    # Show top 10 entity types
    sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    for entity_type, count in sorted_types:
        sanitized = neo4j._sanitize_label(entity_type)
        has_dynamic = any(sanitized in node['node_labels'] for node in all_nodes if node['entity_type'] == entity_type)
        status = "🆕 Dynamic" if has_dynamic else "📋 Static"
        print(f"   {entity_type:25} → :Entity:{sanitized:25} | Count: {count:3} | {status}")
    
    print(f"\n✨ BENEFITS OF DYNAMIC NODE TYPES:")
    print(f"   • More specific and semantic node labels")
    print(f"   • Better performance for type-specific queries")
    print(f"   • Improved graph visualization and navigation")
    print(f"   • Domain-specific optimizations possible")
    print(f"   • Clear separation between different entity types")
    print(f"   • Maintains backward compatibility with :Entity base label")
    
    print(f"\n🔄 MIGRATION STRATEGY:")
    print(f"   • New entities automatically get dynamic labels")
    print(f"   • Old entities continue to work with type property")
    print(f"   • Queries can target both old and new style nodes")
    print(f"   • Gradual migration as new content is processed")
    
    await neo4j.close()


async def demo_domain_specific_extraction():
    """Demonstrate how domain-specific types work with the extraction system."""
    
    print(f"\n🧠 DOMAIN-SPECIFIC EXTRACTION DEMO")
    print("=" * 60)
    
    # Initialize extraction agent
    neo4j = Neo4jManager()
    await neo4j.initialize()
    
    extractor = EntityExtractionAgent(neo4j_manager=neo4j)
    
    # Test documents with different domains
    test_documents = [
        Document(
            id='demo-tech-doc',
            title='API Integration Architecture',
            content="""
            The authentication service validates user credentials via OAuth2.
            The payment gateway processes transactions and integrates with Stripe API.
            The notification service sends emails using SendGrid service.
            The database stores user profiles in PostgreSQL clusters.
            """,
            source_system='demo',
            source_path='tech_doc.md',
            document_type='technical_specification',
            metadata={'domain': 'technical'},
            created_at=datetime.now()
        ),
        Document(
            id='demo-business-doc', 
            title='Team Organization Structure',
            content="""
            Sarah manages the development team and coordinates with external vendors.
            Mike develops the authentication API and implements security features.
            The marketing team analyzes customer data and creates targeted campaigns.
            The sales team tracks leads and manages customer relationships.
            """,
            source_system='demo',
            source_path='business_doc.md', 
            document_type='business_document',
            metadata={'domain': 'business'},
            created_at=datetime.now()
        )
    ]
    
    print(f"\n📄 PROCESSING DOMAIN-SPECIFIC DOCUMENTS:")
    
    for doc in test_documents:
        print(f"\n  📋 Processing: {doc.title}")
        print(f"     Domain: {doc.metadata.get('domain', 'unknown')}")
        
        try:
            entities, relationships = await extractor.extract_entities_and_relationships(doc)
            print(f"     ✅ Extracted {len(entities)} entities, {len(relationships)} relationships")
            
            # Show the types of entities discovered
            entity_types = {}
            for entity in entities:
                entity_type = entity.entity_type
                entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
            
            print(f"     🏷️ Entity types discovered:")
            for etype, count in entity_types.items():
                sanitized = neo4j._sanitize_label(etype)
                print(f"        • {etype} → :Entity:{sanitized} ({count} entities)")
                
        except Exception as e:
            print(f"     ❌ Extraction failed: {e}")
    
    await neo4j.close()


if __name__ == "__main__":
    # Run the comparison demo
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        print("Starting node type comparison demo...")
        loop.run_until_complete(demo_node_type_comparison())
        
        print("\n" + "="*60)
        loop.run_until_complete(demo_domain_specific_extraction())
        
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        loop.close()
        print(f"\n🏁 Demo completed!")
