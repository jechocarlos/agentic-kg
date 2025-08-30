"""
Test the new verb-focused extraction approach.
"""

import asyncio
from datetime import datetime

from src.akg.agents.extraction import EntityExtractionAgent
from src.akg.models import Document


async def test_verb_focused_extraction():
    # Test document with lots of action verbs
    test_content = """
    # Project Status Update
    
    Sarah Johnson manages the development team and coordinates with stakeholders.
    Mike Chen develops the backend API and integrates with the database.
    Lisa Rodriguez designs the user interface and creates wireframes.
    David Kim analyzes user requirements and documents specifications.
    
    The system processes payments automatically and validates credit cards.
    The API calls external services and returns transaction data.
    The database stores user information and maintains audit logs.
    
    Weekly meetings are scheduled every Monday at 10 AM.
    Sarah assigns tasks to team members based on priorities.
    Mike reviews code submissions and approves pull requests.
    Lisa conducts user testing and gathers feedback.
    
    The budget allocates $300K to development and $100K to testing.
    Project Alpha depends on the completion of Phase 1.
    The timeline requires all features to be delivered by December 31st.
    
    Security measures encrypt sensitive data and protect user privacy.
    Error handling catches exceptions and logs debug information.
    Performance monitoring tracks response times and identifies bottlenecks.
    """
    
    doc = Document(
        id='verb-test',
        title='Project Status Update',
        content=test_content,
        source_system='test',
        source_path='verb_test.md',
        document_type='project_update',
        metadata={},
        created_at=datetime.now()
    )
    
    print("🧪 TESTING VERB-FOCUSED EXTRACTION (with Supabase fallback)")
    print("=" * 60)
    
    extractor = EntityExtractionAgent(supabase_manager=None)  # Test without Supabase
    entities, relationships = await extractor.extract_entities_and_relationships(doc)
    
    print(f"\n📊 EXTRACTION RESULTS:")
    print(f"Entities: {len(entities)}")
    print(f"Relationships: {len(relationships)}")
    print(f"Relationships per Entity: {len(relationships) / len(entities) if entities else 0:.2f}")
    
    print(f"\n👥 ENTITIES:")
    for i, entity in enumerate(entities, 1):
        print(f"  {i:2d}. {entity.name} ({entity.entity_type})")
    
    print(f"\n🔗 VERB-BASED RELATIONSHIPS:")
    entity_lookup = {e.id: e.name for e in entities}
    
    # Group relationships by type to show verb extraction
    verb_relationships = {}
    for rel in relationships:
        source_name = entity_lookup.get(rel.source_entity_id, rel.source_entity_id)
        target_name = entity_lookup.get(rel.target_entity_id, rel.target_entity_id)
        
        verb = rel.relationship_type
        if verb not in verb_relationships:
            verb_relationships[verb] = []
        verb_relationships[verb].append(f"{source_name} -> {target_name}")
    
    for verb, rels in sorted(verb_relationships.items()):
        print(f"\n  🎯 {verb}:")
        for rel in rels[:3]:  # Show first 3 examples
            print(f"     - {rel}")
        if len(rels) > 3:
            print(f"     ... and {len(rels) - 3} more")
    
    print(f"\n📈 VERB DISTRIBUTION:")
    verb_counts = {}
    for rel in relationships:
        verb = rel.relationship_type
        verb_counts[verb] = verb_counts.get(verb, 0) + 1
    
    for verb, count in sorted(verb_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {verb}: {count}")
    
    # Analyze how many relationships extracted per entity
    entity_rel_count = {}
    for rel in relationships:
        source_id = rel.source_entity_id
        entity_rel_count[source_id] = entity_rel_count.get(source_id, 0) + 1
    
    print(f"\n🎲 RELATIONSHIPS PER ENTITY:")
    for entity in entities[:8]:  # Show top 8
        count = entity_rel_count.get(entity.id, 0)
        print(f"  - {entity.name}: {count} relationships")

if __name__ == "__main__":
    asyncio.run(test_verb_focused_extraction())
