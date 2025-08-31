#!/usr/bin/env python3
"""
Test script to verify coreference resolution is working correctly.
"""

import asyncio
import logging
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime

from src.akg.agents.coreference_resolver import CoreferenceResolver
from src.akg.models import Entity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_coreference_resolution():
    """Test the coreference resolution system."""
    print("🧪 Testing Coreference Resolution System")
    print("=" * 50)
    
    resolver = CoreferenceResolver()
    
    # Create test entities that include pronouns and generic references
    test_entities = [
        Entity(
            id="1",
            name="OpenAI",
            entity_type="ORGANIZATION",
            document_id="test_doc",
            properties={},
            confidence_score=0.9,
            created_at=datetime.utcnow()
        ),
        Entity(
            id="2", 
            name="ChatGPT",
            entity_type="SERVICE",
            document_id="test_doc",
            properties={},
            confidence_score=0.9,
            created_at=datetime.utcnow()
        ),
        Entity(
            id="3",
            name="User",
            entity_type="PARTY",
            document_id="test_doc", 
            properties={},
            confidence_score=0.9,
            created_at=datetime.utcnow()
        ),
        Entity(
            id="4",
            name="Privacy Policy",
            entity_type="POLICY_DOCUMENT",
            document_id="test_doc",
            properties={},
            confidence_score=0.9,
            created_at=datetime.utcnow()
        ),
        # Pronoun entities that should be resolved
        Entity(
            id="5",
            name="we",
            entity_type="PARTY",
            document_id="test_doc",
            properties={},
            confidence_score=0.7,
            created_at=datetime.utcnow()
        ),
        Entity(
            id="6",
            name="you",
            entity_type="PARTY",
            document_id="test_doc",
            properties={},
            confidence_score=0.7,
            created_at=datetime.utcnow()
        ),
        Entity(
            id="7",
            name="the company",
            entity_type="ORGANIZATION",
            document_id="test_doc",
            properties={},
            confidence_score=0.7,
            created_at=datetime.utcnow()
        ),
        Entity(
            id="8",
            name="the service",
            entity_type="SERVICE",
            document_id="test_doc",
            properties={},
            confidence_score=0.7,
            created_at=datetime.utcnow()
        ),
        Entity(
            id="9",
            name="this policy",
            entity_type="POLICY_DOCUMENT",
            document_id="test_doc",
            properties={},
            confidence_score=0.7,
            created_at=datetime.utcnow()
        )
    ]
    
    print(f"📋 Input entities ({len(test_entities)}):")
    for entity in test_entities:
        print(f"  - '{entity.name}' (type: {entity.entity_type})")
    
    print("\n🔍 Applying coreference resolution...")
    
    # Test resolution for privacy policy context
    resolved_entities = await resolver.resolve_coreferences_in_entities(
        test_entities, 
        document_context='privacy_policy'
    )
    
    print(f"\n✅ Resolved entities ({len(resolved_entities)}):")
    for entity in resolved_entities:
        print(f"  - '{entity.name}' (type: {entity.entity_type})")
    
    # Show the mapping
    print(f"\n🎯 Resolution Summary:")
    print(f"  Original entities: {len(test_entities)}")
    print(f"  Resolved entities: {len(resolved_entities)}")
    print(f"  Pronouns resolved: {len(test_entities) - len(resolved_entities)}")
    
    # Verify expected resolutions
    entity_names = [e.name for e in resolved_entities]
    expected_reductions = ['we', 'you', 'the company', 'the service', 'this policy']
    
    print(f"\n🔍 Verification:")
    for pronoun in expected_reductions:
        if pronoun not in entity_names:
            print(f"  ✅ '{pronoun}' was successfully resolved")
        else:
            print(f"  ❌ '{pronoun}' was NOT resolved")
    
    if len(resolved_entities) < len(test_entities):
        print(f"\n🎉 SUCCESS: Coreference resolution is working!")
        print(f"   Reduced {len(test_entities)} entities to {len(resolved_entities)} entities")
    else:
        print(f"\n⚠️  WARNING: No entities were resolved")

if __name__ == "__main__":
    asyncio.run(test_coreference_resolution())
