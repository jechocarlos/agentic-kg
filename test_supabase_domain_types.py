"""
Test Supabase integration for domain-specific fallback types.
"""

import asyncio
import os
from datetime import datetime

from src.akg.agents.extraction import EntityExtractionAgent
from src.akg.database.supabase_manager import SupabaseManager
from src.akg.models import Document


async def test_supabase_domain_types():
    """Test storing and retrieving domain-specific types in Supabase."""
    
    # Initialize Supabase manager (requires environment variables)
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL and SUPABASE_ANON_KEY environment variables required")
        print("💡 Set these in your environment to test Supabase integration")
        return
    
    supabase_manager = SupabaseManager(supabase_url, supabase_key)
    
    try:
        await supabase_manager.initialize()
        print("✅ Supabase initialized successfully")
        
        # Create extraction agent with Supabase integration
        extractor = EntityExtractionAgent(supabase_manager=supabase_manager)
        
        # Test document with domain-specific content
        test_content = """
        # API Integration Project
        
        The authentication service validates user credentials and returns JWT tokens.
        The payment gateway processes credit card transactions and integrates with the bank API.
        The notification service sends email alerts when payments are completed.
        
        Sarah manages the development team and coordinates with external vendors.
        Mike develops the authentication API and implements OAuth2 security.
        The database stores user profiles and maintains transaction history.
        """
        
        doc = Document(
            id='supabase-test',
            title='API Integration Project',
            content=test_content,
            source_system='test',
            source_path='supabase_test.md',
            document_type='technical_specification',
            metadata={},
            created_at=datetime.now()
        )
        
        print("🧪 TESTING SUPABASE DOMAIN TYPE STORAGE")
        print("=" * 60)
        
        # Extract entities and relationships (this will store domain types)
        entities, relationships = await extractor.extract_entities_and_relationships(doc)
        
        print(f"\n📊 EXTRACTION RESULTS:")
        print(f"Entities: {len(entities)}")
        print(f"Relationships: {len(relationships)}")
        
        # Test retrieving domain types from Supabase
        print(f"\n🔍 RETRIEVING DOMAIN TYPES FROM SUPABASE:")
        
        # Get technical domain entity types
        technical_entities = await supabase_manager.get_domain_entity_types('technical')
        print(f"\nTechnical Entity Types ({len(technical_entities)}):")
        for entity_type in technical_entities[:5]:
            print(f"  - {entity_type['entity_type']} (usage: {entity_type['usage_count']}, confidence: {entity_type['confidence_score']:.2f})")
        
        # Get technical domain relationship types
        technical_relationships = await supabase_manager.get_domain_relationship_types('technical')
        print(f"\nTechnical Relationship Types ({len(technical_relationships)}):")
        for rel_type in technical_relationships[:5]:
            verb = rel_type['source_verb'] or 'N/A'
            print(f"  - {rel_type['relationship_type']} (verb: {verb}, usage: {rel_type['usage_count']})")
        
        # Get business domain types
        business_entities = await supabase_manager.get_domain_entity_types('business')
        if business_entities:
            print(f"\nBusiness Entity Types ({len(business_entities)}):")
            for entity_type in business_entities[:3]:
                print(f"  - {entity_type['entity_type']} (usage: {entity_type['usage_count']})")
        
        # Get domain statistics
        stats = await supabase_manager.get_domain_statistics()
        print(f"\n📈 DOMAIN STATISTICS:")
        print(f"Total Entity Types: {stats['total_entity_types']}")
        print(f"Total Relationship Types: {stats['total_relationship_types']}")
        print(f"Total Verb Extractions: {stats['total_verb_extractions']}")
        
        # Show domain breakdown
        if stats['domain_statistics']:
            print(f"\nDomain Breakdown:")
            for domain_stat in stats['domain_statistics'][:5]:
                print(f"  - {domain_stat['domain']}: {domain_stat['entity_types_count']} entity types, {domain_stat['relationship_types_count']} relationship types")
        
        print(f"\n✅ SUPABASE INTEGRATION TEST COMPLETED!")
        
    except Exception as e:
        print(f"❌ Error testing Supabase integration: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await supabase_manager.close()

async def test_fallback_without_supabase():
    """Test that extraction still works without Supabase."""
    print("\n🧪 TESTING FALLBACK WITHOUT SUPABASE")
    print("=" * 60)
    
    # Create extraction agent without Supabase
    extractor = EntityExtractionAgent(supabase_manager=None)
    
    test_content = """
    The marketing team analyzes customer data and creates targeted campaigns.
    The CRM system stores customer information and tracks sales opportunities.
    """
    
    doc = Document(
        id='fallback-test',
        title='Marketing Analysis',
        content=test_content,
        source_system='test',
        source_path='fallback_test.md',
        document_type='business_report',
        metadata={},
        created_at=datetime.now()
    )
    
    entities, relationships = await extractor.extract_entities_and_relationships(doc)
    
    print(f"✅ Fallback extraction successful:")
    print(f"  - Entities: {len(entities)}")
    print(f"  - Relationships: {len(relationships)}")

if __name__ == "__main__":
    import sys

    # Test with Supabase if credentials available
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(test_supabase_domain_types())
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted")
    finally:
        # Always test fallback
        loop.run_until_complete(test_fallback_without_supabase())
        loop.close()
