"""
Tests for the EntityExtractionAgent class.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from akg.agents.extraction import EntityExtractionAgent
from akg.models import Document, Entity, Relationship


class TestEntityExtractionAgent:
    """Test cases for EntityExtractionAgent functionality."""
    
    @pytest.fixture
    def extraction_agent(self, mock_neo4j_manager):
        """Create an EntityExtractionAgent for testing."""
        with patch('akg.agents.extraction.genai') as mock_genai:
            mock_genai.configure = Mock()
            mock_genai.GenerativeModel = Mock()
            agent = EntityExtractionAgent(neo4j_manager=mock_neo4j_manager)
            return agent
    
    def test_initialization_without_neo4j(self):
        """Test initialization without Neo4j manager."""
        with patch('akg.agents.extraction.genai') as mock_genai:
            mock_genai.configure = Mock()
            mock_genai.GenerativeModel = Mock()
            agent = EntityExtractionAgent(neo4j_manager=None)
            assert agent.neo4j_manager is None
            assert agent.type_manager is not None
    
    @pytest.mark.asyncio
    async def test_extract_entities_and_relationships_with_gemini(self, extraction_agent, sample_document, mock_gemini_model):
        """Test entity extraction using Gemini."""
        extraction_agent.model = mock_gemini_model
        extraction_agent.type_manager._cache_updated = True
        extraction_agent.type_manager._entity_types_cache = {"organization", "person"}
        extraction_agent.type_manager._relationship_types_cache = {"founded"}
        
        # Mock type resolution
        extraction_agent.type_manager.resolve_entity_type = AsyncMock(side_effect=[
            ("organization", False),  # Microsoft Corporation
            ("person", False)         # Bill Gates
        ])
        extraction_agent.type_manager.resolve_relationship_type = AsyncMock(return_value=("founded", False))
        
        entities, relationships = await extraction_agent.extract_entities_and_relationships(sample_document)
        
        assert len(entities) == 2
        assert len(relationships) == 1
        assert entities[0].name == "Microsoft Corporation"
        assert entities[0].entity_type == "organization"
        assert entities[1].name == "Bill Gates"
        assert entities[1].entity_type == "person"
        assert relationships[0].relationship_type == "founded"
    
    @pytest.mark.asyncio
    async def test_extract_entities_fallback_when_gemini_fails(self, extraction_agent, sample_document):
        """Test fallback to pattern extraction when Gemini fails."""
        extraction_agent.model = None  # Simulate Gemini not available
        extraction_agent.type_manager._cache_updated = True
        
        # Mock fallback extractor
        mock_entity = Entity(
            id="test-entity",
            name="Test Entity",
            entity_type="organization",
            document_id=sample_document.id,
            confidence_score=0.7
        )
        mock_relationship = Relationship(
            id="test-rel",
            source_entity_id="entity-1",
            target_entity_id="entity-2",
            relationship_type="mentions",
            document_id=sample_document.id,
            confidence_score=0.6
        )
        
        extraction_agent.fallback_extractor.extract_entities = Mock(return_value=[mock_entity])
        extraction_agent.fallback_extractor.extract_relationships = Mock(return_value=[mock_relationship])
        
        # Mock type resolution for fallback
        extraction_agent.type_manager.resolve_entity_type = AsyncMock(return_value=("organization", False))
        extraction_agent.type_manager.resolve_relationship_type = AsyncMock(return_value=("mentions", False))
        
        entities, relationships = await extraction_agent.extract_entities_and_relationships(sample_document)
        
        assert len(entities) == 1
        assert len(relationships) == 1
        assert entities[0].entity_type == "organization"
        assert relationships[0].relationship_type == "mentions"
    
    @pytest.mark.asyncio
    async def test_parse_gemini_response_with_type_resolution(self, extraction_agent, sample_document):
        """Test parsing Gemini response with type resolution."""
        extraction_agent.type_manager.resolve_entity_type = AsyncMock(side_effect=[
            ("organization", False),
            ("person", True)  # New type
        ])
        extraction_agent.type_manager.resolve_relationship_type = AsyncMock(return_value=("founded", True))
        
        response_text = '''
        {
            "entities": [
                {
                    "name": "Microsoft Corporation",
                    "type": "company",
                    "aliases": ["Microsoft"],
                    "properties": {"industry": "technology"},
                    "confidence": 0.9
                },
                {
                    "name": "Bill Gates",
                    "type": "individual",
                    "aliases": [],
                    "properties": {"role": "founder"},
                    "confidence": 0.8
                }
            ],
            "relationships": [
                {
                    "source_entity": "Bill Gates",
                    "target_entity": "Microsoft Corporation",
                    "type": "established",
                    "properties": {"year": "1975"},
                    "confidence": 0.9
                }
            ]
        }
        '''
        
        entities, relationships = await extraction_agent._parse_gemini_response_with_type_resolution(
            response_text, sample_document.id
        )
        
        assert len(entities) == 2
        assert len(relationships) == 1
        
        # Check that type resolution was called
        extraction_agent.type_manager.resolve_entity_type.assert_any_call("company")
        extraction_agent.type_manager.resolve_entity_type.assert_any_call("individual")
        extraction_agent.type_manager.resolve_relationship_type.assert_called_with("established")
        
        # Check resolved types
        assert entities[0].entity_type == "organization"  # Resolved from "company"
        assert entities[1].entity_type == "person"  # Resolved from "individual"
        assert relationships[0].relationship_type == "founded"  # Resolved from "established"
    
    @pytest.mark.asyncio
    async def test_parse_malformed_json_response(self, extraction_agent, sample_document):
        """Test handling of malformed JSON response."""
        malformed_response = "This is not valid JSON"
        
        entities, relationships = await extraction_agent._parse_gemini_response_with_type_resolution(
            malformed_response, sample_document.id
        )
        
        assert len(entities) == 0
        assert len(relationships) == 0
    
    @pytest.mark.asyncio
    async def test_apply_type_resolution_to_fallback(self, extraction_agent):
        """Test applying type resolution to fallback extraction results."""
        # Create sample fallback results
        fallback_entity = Entity(
            id="test-entity",
            name="Test Entity",
            entity_type="company",  # Original type
            document_id="test-doc",
            confidence_score=0.7
        )
        fallback_relationship = Relationship(
            id="test-rel",
            source_entity_id="entity-1",
            target_entity_id="entity-2",
            relationship_type="established",  # Original type
            document_id="test-doc",
            confidence_score=0.6
        )
        
        # Mock type resolution
        extraction_agent.type_manager.resolve_entity_type = AsyncMock(return_value=("organization", False))
        extraction_agent.type_manager.resolve_relationship_type = AsyncMock(return_value=("founded", False))
        
        resolved_entities, resolved_relationships = await extraction_agent._apply_type_resolution_to_fallback(
            [fallback_entity], [fallback_relationship]
        )
        
        assert len(resolved_entities) == 1
        assert len(resolved_relationships) == 1
        assert resolved_entities[0].entity_type == "organization"  # Type was resolved
        assert resolved_relationships[0].relationship_type == "founded"  # Type was resolved
    
    @pytest.mark.asyncio
    async def test_save_to_neo4j_success(self, extraction_agent, sample_entity, sample_relationship):
        """Test successful saving to Neo4j."""
        extraction_agent.neo4j_manager.create_entity.return_value = True
        extraction_agent.neo4j_manager.create_relationship.return_value = True
        
        result = await extraction_agent.save_to_neo4j([sample_entity], [sample_relationship])
        
        assert result is True
        extraction_agent.neo4j_manager.create_entity.assert_called_once()
        extraction_agent.neo4j_manager.create_relationship.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_to_neo4j_failure(self, extraction_agent, sample_entity):
        """Test saving to Neo4j when creation fails."""
        extraction_agent.neo4j_manager.create_entity.side_effect = Exception("Database error")
        
        result = await extraction_agent.save_to_neo4j([sample_entity], [])
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_save_to_neo4j_without_manager(self, sample_entity):
        """Test saving when Neo4j manager is not available."""
        agent = EntityExtractionAgent(neo4j_manager=None)
        
        result = await agent.save_to_neo4j([sample_entity], [])
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_process_document_complete_workflow(self, extraction_agent, sample_document):
        """Test the complete document processing workflow."""
        # Mock the extraction
        mock_entity = Entity(
            id="test-entity",
            name="Test Entity",
            entity_type="organization",
            document_id=sample_document.id,
            confidence_score=0.8
        )
        mock_relationship = Relationship(
            id="test-rel",
            source_entity_id="entity-1",
            target_entity_id="entity-2",
            relationship_type="mentions",
            document_id=sample_document.id,
            confidence_score=0.7
        )
        
        extraction_agent.extract_entities_and_relationships = AsyncMock(
            return_value=([mock_entity], [mock_relationship])
        )
        extraction_agent.save_to_neo4j = AsyncMock(return_value=True)
        
        result = await extraction_agent.process_document(sample_document)
        
        assert result["document_id"] == sample_document.id
        assert result["entities_count"] == 1
        assert result["relationships_count"] == 1
        assert result["neo4j_saved"] is True
        assert len(result["entities"]) == 1
        assert len(result["relationships"]) == 1
    
    @pytest.mark.asyncio
    async def test_process_documents_multiple(self, extraction_agent):
        """Test processing multiple documents."""
        documents = [
            Document(id="doc1", title="Doc 1", content="Content 1", source_system="test", source_path="/test1", document_type="txt"),
            Document(id="doc2", title="Doc 2", content="Content 2", source_system="test", source_path="/test2", document_type="txt")
        ]
        
        extraction_agent.process_document = AsyncMock(side_effect=[
            {"document_id": "doc1", "entities_count": 2, "relationships_count": 1, "neo4j_saved": True},
            {"document_id": "doc2", "entities_count": 1, "relationships_count": 2, "neo4j_saved": True}
        ])
        
        results = await extraction_agent.process_documents(documents)
        
        assert len(results) == 2
        assert results[0]["document_id"] == "doc1"
        assert results[1]["document_id"] == "doc2"
    
    def test_create_extraction_prompt_with_existing_types(self, extraction_agent, sample_document):
        """Test creation of extraction prompt with existing types."""
        existing_entity_types = ["person", "organization", "location"]
        existing_relationship_types = ["works_for", "founded_by", "located_in"]
        
        prompt = extraction_agent._create_extraction_prompt(
            sample_document, existing_entity_types, existing_relationship_types
        )
        
        # Check that all entity types are present in the prompt
        assert "person" in prompt
        assert "organization" in prompt
        assert "location" in prompt
        
        # Check that all relationship types are present in the prompt
        assert "works_for" in prompt
        assert "founded_by" in prompt
        assert "located_in" in prompt
        assert sample_document.title in prompt
        assert sample_document.content in prompt
    
    def test_create_extraction_prompt_without_existing_types(self, extraction_agent, sample_document):
        """Test creation of extraction prompt without existing types."""
        prompt = extraction_agent._create_extraction_prompt(sample_document, [], [])
        
        assert "No existing entity types found" in prompt
        assert "No existing relationship types found" in prompt
        assert sample_document.title in prompt
        assert sample_document.content in prompt
