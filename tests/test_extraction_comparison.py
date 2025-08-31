"""
Test script to compare relationship extraction before and after improvements.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the parent directory to the path to access src
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.akg.agents.extraction import EntityExtractionAgent
from src.akg.models import Document


async def test_extraction_improvements():
    # Create a simple test document
    test_content = """
    # Project Alpha Meeting Notes
    
    **Date:** August 15, 2024
    **Attendees:**
    - Sarah Johnson (Project Manager) 
    - Mike Chen (Senior Developer)
    - Lisa Rodriguez (UX Designer)
    
    ## Key Decisions
    Project Alpha will use React for the frontend and Node.js for the backend.
    Sarah Johnson will manage the overall project timeline.
    Mike Chen will lead the technical implementation.
    Lisa Rodriguez will design the user interface.
    
    ## Action Items
    1. David Kim will create user requirements by August 22, 2024
    2. Mike Chen will set up development environment by August 20, 2024
    3. Sarah Johnson will schedule weekly check-ins with stakeholders
    
    ## Budget
    Project Alpha has a budget of $500,000 approved by John Smith (CTO).
    """
    
    doc = Document(
        id='test-doc',
        title='Test Meeting Notes',
        content=test_content,
        source_system='test',
        source_path='test.md',
        document_type='meeting_notes',
        metadata={},
        created_at=datetime.now()
    )
    
    print("🧪 Testing Enhanced Extraction Prompt")
    print("=" * 50)
    
    extractor = EntityExtractionAgent()
    entities, relationships = await extractor.extract_entities_and_relationships(doc)
    
    print(f"\n📊 RESULTS:")
    print(f"Total Entities: {len(entities)}")
    print(f"Total Relationships: {len(relationships)}")
    print(f"Relationships per Entity: {len(relationships) / len(entities):.2f}")
    
    print(f"\n👥 ENTITIES ({len(entities)}):")
    for i, entity in enumerate(entities, 1):
        print(f"  {i:2d}. {entity.name} ({entity.entity_type})")
    
    print(f"\n🔗 RELATIONSHIPS ({len(relationships)}):")
    entity_lookup = {e.id: e.name for e in entities}
    
    for i, rel in enumerate(relationships, 1):
        source_name = entity_lookup.get(rel.source_entity_id, rel.source_entity_id)
        target_name = entity_lookup.get(rel.target_entity_id, rel.target_entity_id)
        print(f"  {i:2d}. {source_name} --[{rel.relationship_type}]--> {target_name}")
    
    # Analyze relationship types
    rel_types = {}
    for rel in relationships:
        rel_types[rel.relationship_type] = rel_types.get(rel.relationship_type, 0) + 1
    
    print(f"\n📈 RELATIONSHIP TYPE DISTRIBUTION:")
    for rel_type, count in sorted(rel_types.items()):
        print(f"  - {rel_type}: {count}")
    
    # Check for comprehensive extraction
    expected_relationships = [
        "Project management roles", 
        "Technical responsibilities",
        "Design responsibilities",
        "Technology stack relationships",
        "Approval relationships",
        "Budget relationships", 
        "Timeline/deadline relationships",
        "Action item assignments"
    ]
    
    print(f"\n✅ COVERAGE ANALYSIS:")
    print("Expected relationship categories found:")
    
    has_management = any("MANAGE" in rel.relationship_type for rel in relationships)
    has_tech = any("TECHNOLOGY" in rel.relationship_type or "LEAD" in rel.relationship_type for rel in relationships)
    has_approval = any("APPROVED" in rel.relationship_type for rel in relationships)
    has_budget = any("BUDGET" in rel.relationship_type or "HAS" in rel.relationship_type for rel in relationships)
    has_timeline = any("WILL" in rel.relationship_type or "BY" in rel.relationship_type for rel in relationships)
    
    print(f"  ✓ Management relationships: {has_management}")
    print(f"  ✓ Technical relationships: {has_tech}")
    print(f"  ✓ Approval relationships: {has_approval}")
    print(f"  ✓ Budget/property relationships: {has_budget}")
    print(f"  ✓ Timeline relationships: {has_timeline}")

if __name__ == "__main__":
    asyncio.run(test_extraction_improvements())
