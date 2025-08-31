"""
Tests for the Neo4j database manager.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from akg.database.neo4j_manager import Neo4jManager


class TestNeo4jManager:
    """Test cases for Neo4jManager functionality."""
    
    def _create_mock_session_driver(self, mock_session):
        """Helper to create a properly mocked driver with session context manager."""
        class MockAsyncContextManager:
            def __init__(self, session):
                self.session = session
            
            async def __aenter__(self):
                return self.session
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        
        mock_driver = AsyncMock()
        mock_driver.session = Mock(return_value=MockAsyncContextManager(mock_session))
        return mock_driver
    
    @pytest.fixture
    def neo4j_manager(self):
        """Create a Neo4jManager for testing."""
        return Neo4jManager(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="test_password"
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, neo4j_manager):
        """Test Neo4j manager initialization."""
        with patch('akg.database.neo4j_manager.AsyncGraphDatabase') as mock_graph_db, \
             patch.object(neo4j_manager, '_create_constraints_and_indexes') as mock_constraints:
            
            mock_driver = AsyncMock()
            mock_driver.verify_connectivity = AsyncMock()
            mock_graph_db.driver.return_value = mock_driver
            mock_constraints.return_value = None
            
            await neo4j_manager.initialize()
            
            assert neo4j_manager.driver is not None
            mock_graph_db.driver.assert_called_once_with(
                "bolt://localhost:7687",
                auth=("neo4j", "test_password")
            )
            mock_driver.verify_connectivity.assert_called_once()
            mock_constraints.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_connection(self, neo4j_manager):
        """Test closing Neo4j connection."""
        mock_driver = AsyncMock()
        neo4j_manager.driver = mock_driver
        
        await neo4j_manager.close()
        
        mock_driver.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_entity_success(self, neo4j_manager):
        """Test successful entity creation."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_record = Mock()

        # Create a proper mock record that can be accessed like a dict
        # The 'e' key should return a mock entity object
        mock_entity = {"id": "test-entity", "name": "Test Entity"}
        record_data = {"e": mock_entity}
        mock_record.__getitem__ = Mock(side_effect=lambda key: record_data[key])
        mock_record.data.return_value = record_data

        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        mock_driver = self._create_mock_session_driver(mock_session)
        neo4j_manager.driver = mock_driver

        result = await neo4j_manager.create_entity(
            entity_id="test-entity",
            name="Test Entity",
            entity_type="person",
            document_id="doc-123",
            properties={"age": 30},
            confidence=0.9
        )

        assert result is True
        # Should be called twice: once for entity creation, once for linking to document
        assert mock_session.run.call_count == 2
    
    @pytest.mark.asyncio
    async def test_create_entity_failure(self, neo4j_manager):
        """Test entity creation failure."""
        mock_session = AsyncMock()
        mock_session.run.side_effect = Exception("Database error")
        
        mock_driver = AsyncMock()
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        neo4j_manager.driver = mock_driver
        
        result = await neo4j_manager.create_entity(
            entity_id="test-entity",
            name="Test Entity",
            entity_type="person",
            document_id="doc-123"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_create_relationship_success(self, neo4j_manager):
        """Test successful relationship creation."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.consume.return_value = None
        mock_session.run.return_value = mock_result
        
        mock_driver = self._create_mock_session_driver(mock_session)
        neo4j_manager.driver = mock_driver
        
        result = await neo4j_manager.create_relationship(
            source_entity_id="entity-1",
            target_entity_id="entity-2",
            relationship_type="works_for",
            document_id="doc-123",
            properties={"since": "2020"},
            confidence=0.8
        )
        
        assert result is True
        mock_session.run.assert_called_once()
        mock_session.run.assert_called()
    
    @pytest.mark.asyncio
    async def test_create_relationship_failure(self, neo4j_manager):
        """Test relationship creation failure."""
        mock_session = AsyncMock()
        mock_session.run.side_effect = Exception("Database error")
        
        mock_driver = AsyncMock()
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        neo4j_manager.driver = mock_driver
        
        result = await neo4j_manager.create_relationship(
            source_entity_id="entity-1",
            target_entity_id="entity-2",
            relationship_type="works_for",
            document_id="doc-123"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_existing_entity_types(self, neo4j_manager):
        """Test getting existing entity types."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        
        # Mock async iteration
        records = [
            {"type": "person"},
            {"type": "organization"},
            {"type": "location"}
        ]
        mock_records = []
        for record in records:
            mock_record = Mock()
            mock_record.__getitem__ = Mock(side_effect=lambda key, r=record: r[key])
            mock_records.append(mock_record)
        mock_result.__aiter__.return_value = iter(mock_records)
        mock_session.run.return_value = mock_result
        
        mock_driver = self._create_mock_session_driver(mock_session)
        neo4j_manager.driver = mock_driver
        
        types = await neo4j_manager.get_existing_entity_types()
        
        assert "person" in types
        assert "organization" in types
        assert "location" in types
        assert len(types) == 3
        assert "organization" in types
        assert "location" in types
        assert len(types) == 3
    
    @pytest.mark.asyncio
    async def test_get_existing_relationship_types(self, neo4j_manager):
        """Test getting existing relationship types."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        
        # Mock async iteration
        records = [
            {"type": "works_for"},
            {"type": "founded_by"},
            {"type": "located_in"}
        ]
        mock_records = []
        for record in records:
            mock_record = Mock()
            mock_record.__getitem__ = Mock(side_effect=lambda key, r=record: r[key])
            mock_records.append(mock_record)
        mock_result.__aiter__.return_value = iter(mock_records)
        mock_session.run.return_value = mock_result
        
        mock_driver = self._create_mock_session_driver(mock_session)
        neo4j_manager.driver = mock_driver
        
        types = await neo4j_manager.get_existing_relationship_types()
        
        assert "works_for" in types
        assert "founded_by" in types
        assert "located_in" in types
        assert len(types) == 3
        assert "founded_by" in types
        assert "located_in" in types
        assert len(types) == 3
    
    @pytest.mark.asyncio
    async def test_get_entity_by_name_and_type(self, neo4j_manager):
        """Test getting entity by name and type."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        
        # Create a mock record with proper __getitem__ support
        record_data = {
            "id": "entity-123",
            "name": "Microsoft Corporation",
            "type": "organization",
            "confidence": 0.9,
            "properties": {"industry": "technology"}
        }
        mock_record = Mock()
        mock_record.__getitem__ = Mock(side_effect=lambda key: record_data[key])
        
        # Mock the async iteration properly
        async def mock_async_iter(*args):
            yield mock_record
        
        mock_result.__aiter__ = mock_async_iter
        mock_session.run.return_value = mock_result
        
        mock_driver = self._create_mock_session_driver(mock_session)
        neo4j_manager.driver = mock_driver
        
        entity = await neo4j_manager.get_entity_by_name_and_type("Microsoft Corporation", "organization")
        
        assert entity is not None
        assert entity["name"] == "Microsoft Corporation"
        assert entity["type"] == "organization"
        assert entity["id"] == "entity-123"
    
    @pytest.mark.asyncio
    async def test_get_entity_by_name_and_type_not_found(self, neo4j_manager):
        """Test getting entity that doesn't exist."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.__aiter__.return_value = iter([])  # No records
        mock_session.run.return_value = mock_result
        
        mock_driver = self._create_mock_session_driver(mock_session)
        neo4j_manager.driver = mock_driver
        
        entity = await neo4j_manager.get_entity_by_name_and_type("Nonexistent Entity", "organization")
        
        assert entity is None
    
    @pytest.mark.asyncio
    async def test_find_similar_entities(self, neo4j_manager):
        """Test finding similar entities."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        
        # Create mock records with proper __getitem__ support
        record1_data = {
            "id": "entity-1",
            "name": "Microsoft Corporation",
            "type": "organization",
            "confidence": 0.9,
            "properties": {}
        }
        record2_data = {
            "id": "entity-2", 
            "name": "Microsoft Inc",
            "type": "organization",
            "confidence": 0.8,
            "properties": {}
        }
        
        mock_record1 = Mock()
        mock_record1.__getitem__ = Mock(side_effect=lambda key: record1_data[key])
        mock_record2 = Mock()
        mock_record2.__getitem__ = Mock(side_effect=lambda key: record2_data[key])
        
        mock_result.__aiter__.return_value = iter([mock_record1, mock_record2])
        mock_session.run.return_value = mock_result
        
        mock_driver = self._create_mock_session_driver(mock_session)
        neo4j_manager.driver = mock_driver
        
        entities = await neo4j_manager.find_similar_entities("Microsoft")
        
        assert len(entities) == 2
        assert entities[0]["name"] == "Microsoft Corporation"
        assert entities[1]["name"] == "Microsoft Inc"
    
    @pytest.mark.asyncio
    async def test_get_graph_stats(self, neo4j_manager):
        """Test getting graph statistics."""
        mock_session = AsyncMock()
        
        # Create mock results for the three separate queries
        mock_entity_result = AsyncMock()
        mock_rel_result = AsyncMock()
        mock_doc_result = AsyncMock()
        
        # Create mock records for each count query
        entity_record = Mock()
        entity_record.__getitem__ = Mock(side_effect=lambda key: 100 if key == "count" else None)
        
        rel_record = Mock()
        rel_record.__getitem__ = Mock(side_effect=lambda key: 250 if key == "count" else None)
        
        doc_record = Mock()
        doc_record.__getitem__ = Mock(side_effect=lambda key: 10 if key == "count" else None)
        
        # Set up async iteration for each result
        async def entity_iter(*args):
            yield entity_record
        
        async def rel_iter(*args):
            yield rel_record
        
        async def doc_iter(*args):
            yield doc_record
        
        mock_entity_result.__aiter__ = entity_iter
        mock_rel_result.__aiter__ = rel_iter
        mock_doc_result.__aiter__ = doc_iter
        
        # Set up session.run to return the appropriate result based on the query
        def run_side_effect(query, *args, **kwargs):
            if "WHERE e.id IS NOT NULL AND NOT e:Document" in query:
                return mock_entity_result
            elif "MATCH ()-[r]->()" in query:
                return mock_rel_result
            elif "MATCH (d:Document)" in query:
                return mock_doc_result
            return AsyncMock()
        
        mock_session.run.side_effect = run_side_effect
        
        mock_driver = self._create_mock_session_driver(mock_session)
        neo4j_manager.driver = mock_driver
        
        stats = await neo4j_manager.get_graph_stats()
        
        assert stats["total_entities"] == 100
        assert stats["total_relationships"] == 250
        assert stats["total_documents"] == 10
    
    @pytest.mark.asyncio
    async def test_create_document_node_success(self, neo4j_manager):
        """Test successful document node creation."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.consume.return_value = None
        mock_session.run.return_value = mock_result
        
        mock_driver = self._create_mock_session_driver(mock_session)
        neo4j_manager.driver = mock_driver
        
        result = await neo4j_manager.create_document_node(
            document_id="doc-123",
            source_path="/test/doc.txt",
            document_type="txt",
            title="Test Document",
            metadata={"size": 1024}
        )
        
        assert result is True
        mock_session.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, neo4j_manager):
        """Test handling of database connection errors."""
        neo4j_manager.driver = None
        
        # Test various operations without driver
        result = await neo4j_manager.create_entity("id", "name", "type", "doc")
        assert result is False
        
        types = await neo4j_manager.get_existing_entity_types()
        assert types == []
        
        entity = await neo4j_manager.get_entity_by_name_and_type("name", "type")
        assert entity is None
