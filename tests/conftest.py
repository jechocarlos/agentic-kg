"""
Test configuration and shared fixtures for the AKG test suite.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from akg.config import AKGConfig
from akg.models import Document, Entity, Relationship


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = Mock(spec=AKGConfig)
    config.documents_input_dir = "/tmp/test_documents"
    config.supported_extensions = ['.txt', '.md', '.pdf']
    config.exclude_patterns_list = ['*.tmp', '*.log']
    config.recursive_scan = True
    config.watch_directory = False
    config.log_level = "INFO"
    config.google_api_key = "test_api_key"
    config.neo4j_uri = "bolt://localhost:7687"
    config.neo4j_username = "neo4j"
    config.neo4j_password = "test_password"
    config.supabase_url = "https://test.supabase.co"
    config.supabase_api_key = "test_supabase_key"
    return config


@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return Document(
        id="test-doc-123",
        title="Test Document",
        content="Microsoft Corporation is a technology company. Bill Gates founded Microsoft in 1975.",
        source_system="test",
        source_path="/test/path/document.txt",
        document_type="txt",
        metadata={"test": "data"},
        processed_at=datetime.utcnow()
    )


@pytest.fixture
def sample_entity():
    """Sample entity for testing."""
    return Entity(
        id="test-entity-123",
        name="Microsoft Corporation",
        entity_type="organization",
        document_id="test-doc-123",
        properties={"industry": "technology"},
        aliases=["Microsoft", "MSFT"],
        confidence_score=0.9,
        created_at=datetime.utcnow()
    )


@pytest.fixture
def sample_relationship():
    """Sample relationship for testing."""
    return Relationship(
        id="test-rel-123",
        source_entity_id="entity-1",
        target_entity_id="entity-2",
        relationship_type="founded_by",
        document_id="test-doc-123",
        properties={"year": "1975"},
        confidence_score=0.8,
        created_at=datetime.utcnow()
    )


@pytest.fixture
def mock_neo4j_manager():
    """Mock Neo4j manager for testing."""
    manager = AsyncMock()
    manager.initialize = AsyncMock()
    manager.close = AsyncMock()
    manager.create_entity = AsyncMock(return_value=True)
    manager.create_relationship = AsyncMock(return_value=True)
    manager.get_entity_by_name_and_type = AsyncMock(return_value=None)
    manager.find_similar_entities = AsyncMock(return_value=[])
    manager.get_existing_entity_types = AsyncMock(return_value=["person", "organization", "location"])
    manager.get_existing_relationship_types = AsyncMock(return_value=["works_for", "founded_by", "located_in"])
    manager.get_graph_stats = AsyncMock(return_value={"total_entities": 10, "total_relationships": 5})
    return manager


@pytest.fixture
def mock_supabase_manager():
    """Mock Supabase manager for testing."""
    manager = AsyncMock()
    manager.initialize = AsyncMock()
    manager.initialize_schema = AsyncMock()
    manager.create_document = AsyncMock(return_value={"id": "test-doc-123"})
    manager.get_document_by_path = AsyncMock(return_value=None)
    manager.get_document_stats = AsyncMock(return_value={"total": 5})
    return manager


@pytest.fixture
def mock_gemini_model():
    """Mock Google Gemini model for testing."""
    model = Mock()
    response = Mock()
    response.text = '''
    {
        "entities": [
            {
                "name": "Microsoft Corporation",
                "type": "organization",
                "aliases": ["Microsoft", "MSFT"],
                "properties": {"industry": "technology"},
                "confidence": 0.9
            },
            {
                "name": "Bill Gates",
                "type": "person",
                "aliases": [],
                "properties": {"role": "founder"},
                "confidence": 0.8
            }
        ],
        "relationships": [
            {
                "source_entity": "Bill Gates",
                "target_entity": "Microsoft Corporation",
                "type": "founded",
                "properties": {"year": "1975"},
                "confidence": 0.9
            }
        ]
    }
    '''
    model.generate_content = Mock(return_value=response)
    return model


@pytest.fixture
def temp_documents_dir(tmp_path):
    """Create a temporary documents directory with sample files."""
    docs_dir = tmp_path / "documents"
    docs_dir.mkdir()
    
    # Create sample files
    (docs_dir / "test1.txt").write_text("This is a test document about Microsoft Corporation.")
    (docs_dir / "test2.md").write_text("# Meeting Notes\nBill Gates discussed the project.")
    (docs_dir / "excluded.tmp").write_text("This should be excluded")
    
    return docs_dir


@pytest.fixture(autouse=True)
def setup_logging():
    """Setup logging for tests."""
    import logging
    logging.basicConfig(level=logging.DEBUG)
