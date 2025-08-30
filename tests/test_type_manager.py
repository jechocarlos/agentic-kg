"""
Tests for the TypeManager class.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from akg.agents.type_manager import TypeManager


class TestTypeManager:
    """Test cases for TypeManager functionality."""
    
    @pytest.fixture
    def type_manager(self, mock_neo4j_manager):
        """Create a TypeManager instance for testing."""
        return TypeManager(neo4j_manager=mock_neo4j_manager, similarity_threshold=0.8)
    
    @pytest.mark.asyncio
    async def test_refresh_type_cache(self, type_manager, mock_neo4j_manager):
        """Test refreshing the type cache from Neo4j."""
        # Setup mock returns
        mock_neo4j_manager.get_existing_entity_types.return_value = ["person", "organization", "location"]
        mock_neo4j_manager.get_existing_relationship_types.return_value = ["works_for", "founded_by"]
        
        # Refresh cache
        await type_manager.refresh_type_cache()
        
        # Verify cache was updated
        assert type_manager._cache_updated
        assert "person" in type_manager._entity_types_cache
        assert "organization" in type_manager._entity_types_cache
        assert "location" in type_manager._entity_types_cache
        assert "works_for" in type_manager._relationship_types_cache
        assert "founded_by" in type_manager._relationship_types_cache
    
    def test_calculate_similarity(self, type_manager):
        """Test string similarity calculation."""
        # Exact match
        assert type_manager._calculate_similarity("person", "person") == 1.0
        
        # Case insensitive
        assert type_manager._calculate_similarity("Person", "person") == 1.0
        
        # Similar strings
        similarity = type_manager._calculate_similarity("organization", "organisation")
        assert 0.8 < similarity < 1.0
        
        # Completely different
        similarity = type_manager._calculate_similarity("person", "location")
        assert similarity < 0.5
    
    def test_find_similar_types(self, type_manager):
        """Test finding similar types from existing types."""
        type_manager._entity_types_cache = {"person", "organization", "location", "document"}
        
        # Find similar types for "organisation" (British spelling)
        similar = type_manager._find_similar_types("organisation", type_manager._entity_types_cache)
        
        # Should find "organization" as similar
        assert len(similar) > 0
        assert similar[0][0] == "organization"
        assert similar[0][1] > 0.8  # High similarity
    
    @pytest.mark.asyncio
    async def test_resolve_entity_type_exact_match(self, type_manager):
        """Test resolving entity type with exact match."""
        type_manager._entity_types_cache = {"person", "organization", "location"}
        type_manager._cache_updated = True
        
        # Test exact match (case insensitive)
        resolved_type, is_new = await type_manager.resolve_entity_type("PERSON")
        assert resolved_type == "person"
        assert not is_new
    
    @pytest.mark.asyncio
    async def test_resolve_entity_type_similar_match(self, type_manager):
        """Test resolving entity type with similar match."""
        type_manager._entity_types_cache = {"person", "organization", "location"}
        type_manager._cache_updated = True
        
        # Test similar match
        resolved_type, is_new = await type_manager.resolve_entity_type("organisation")
        assert resolved_type == "organization"
        assert not is_new
    
    @pytest.mark.asyncio
    async def test_resolve_entity_type_new_type(self, type_manager):
        """Test resolving entity type that creates new type."""
        type_manager._entity_types_cache = {"person", "organization", "location"}
        type_manager._cache_updated = True
        
        # Test completely new type
        resolved_type, is_new = await type_manager.resolve_entity_type("vehicle")
        assert resolved_type == "vehicle"
        assert is_new
        assert "vehicle" in type_manager._entity_types_cache
    
    @pytest.mark.asyncio
    async def test_resolve_relationship_type_exact_match(self, type_manager):
        """Test resolving relationship type with exact match."""
        type_manager._relationship_types_cache = {"works_for", "founded_by", "located_in"}
        type_manager._cache_updated = True
        
        # Test exact match
        resolved_type, is_new = await type_manager.resolve_relationship_type("works_for")
        assert resolved_type == "works_for"
        assert not is_new
    
    @pytest.mark.asyncio
    async def test_resolve_relationship_type_new_type(self, type_manager):
        """Test resolving relationship type that creates new type."""
        type_manager._relationship_types_cache = {"works_for", "founded_by", "located_in"}
        type_manager._cache_updated = True
        
        # Test new type
        resolved_type, is_new = await type_manager.resolve_relationship_type("manages")
        assert resolved_type == "manages"
        assert is_new
        assert "manages" in type_manager._relationship_types_cache
    
    @pytest.mark.asyncio
    async def test_resolve_multiple_entity_types(self, type_manager):
        """Test resolving multiple entity types at once."""
        type_manager._entity_types_cache = {"person", "organization"}
        type_manager._cache_updated = True
        
        proposed_types = ["person", "company", "vehicle"]
        results = await type_manager.resolve_multiple_entity_types(proposed_types)
        
        assert len(results) == 3
        assert results["person"][0] == "person"
        assert not results["person"][1]  # Not new
        assert results["company"][1]  # New type
        assert results["vehicle"][1]  # New type
    
    def test_suggest_entity_types(self, type_manager):
        """Test suggesting entity types based on partial input."""
        type_manager._entity_types_cache = {"person", "personal_info", "organization", "location"}
        
        suggestions = type_manager.suggest_entity_types("per")
        assert "person" in suggestions
        assert "personal_info" in suggestions
        assert "organization" not in suggestions
    
    def test_suggest_relationship_types(self, type_manager):
        """Test suggesting relationship types based on partial input."""
        type_manager._relationship_types_cache = {"works_for", "worked_with", "founded_by", "located_in"}
        
        suggestions = type_manager.suggest_relationship_types("work")
        assert "works_for" in suggestions
        assert "worked_with" in suggestions
        assert "founded_by" not in suggestions
    
    def test_get_type_statistics(self, type_manager):
        """Test getting type statistics."""
        type_manager._entity_types_cache = {"person", "organization", "location"}
        type_manager._relationship_types_cache = {"works_for", "founded_by"}
        type_manager._cache_updated = True
        
        stats = type_manager.get_type_statistics()
        assert stats["entity_types_count"] == 3
        assert stats["relationship_types_count"] == 2
        assert stats["cache_updated"] is True
    
    @pytest.mark.asyncio
    async def test_refresh_cache_without_neo4j(self):
        """Test refreshing cache when Neo4j manager is not available."""
        type_manager = TypeManager(neo4j_manager=None)
        
        # Should not raise an exception
        await type_manager.refresh_type_cache()
        
        # Cache should remain empty
        assert len(type_manager._entity_types_cache) == 0
        assert len(type_manager._relationship_types_cache) == 0
        assert not type_manager._cache_updated
