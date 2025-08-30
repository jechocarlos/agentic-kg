"""
Tests for the data models.
"""

from datetime import datetime

import pytest

from akg.models import Document, Entity, Relationship


class TestDocument:
    """Test cases for Document model."""
    
    def test_document_creation(self):
        """Test creating a Document instance."""
        doc = Document(
            id="test-123",
            title="Test Document",
            content="This is test content.",
            source_system="test_system",
            source_path="/test/path.txt",
            document_type="txt",
            metadata={"key": "value"},
            processed_at=datetime.utcnow()
        )
        
        assert doc.id == "test-123"
        assert doc.title == "Test Document"
        assert doc.content == "This is test content."
        assert doc.source_system == "test_system"
        assert doc.source_path == "/test/path.txt"
        assert doc.document_type == "txt"
        assert doc.metadata == {"key": "value"}
        assert isinstance(doc.processed_at, datetime)
    
    def test_document_optional_fields(self):
        """Test Document with optional fields."""
        doc = Document(
            id="test-123",
            title="Test Document",
            content="Content",
            source_system="test",
            source_path="/test/path.txt",
            document_type="txt"
        )
        
        assert doc.metadata == {}
        assert doc.processed_at is None
    
    def test_document_dict_serialization(self):
        """Test Document serialization to dict."""
        doc = Document(
            id="test-123",
            title="Test Document",
            content="Content",
            source_system="test",
            source_path="/test/path.txt",
            document_type="txt",
            metadata={"test": True}
        )
        
        doc_dict = doc.dict()
        assert doc_dict["id"] == "test-123"
        assert doc_dict["title"] == "Test Document"
        assert doc_dict["metadata"]["test"] is True


class TestEntity:
    """Test cases for Entity model."""
    
    def test_entity_creation(self):
        """Test creating an Entity instance."""
        entity = Entity(
            id="entity-123",
            name="Microsoft Corporation",
            entity_type="organization",
            document_id="doc-123",
            properties={"industry": "technology"},
            aliases=["Microsoft", "MSFT"],
            confidence_score=0.9,
            created_at=datetime.utcnow()
        )
        
        assert entity.id == "entity-123"
        assert entity.name == "Microsoft Corporation"
        assert entity.entity_type == "organization"
        assert entity.document_id == "doc-123"
        assert entity.properties == {"industry": "technology"}
        assert entity.aliases == ["Microsoft", "MSFT"]
        assert entity.confidence_score == 0.9
        assert isinstance(entity.created_at, datetime)
    
    def test_entity_optional_fields(self):
        """Test Entity with optional fields."""
        entity = Entity(
            id="entity-123",
            name="Test Entity",
            entity_type="person"
        )
        
        assert entity.document_id is None
        assert entity.properties == {}
        assert entity.aliases == []
        assert entity.confidence_score == 0.0
        assert isinstance(entity.created_at, datetime)
    
    def test_entity_confidence_score_validation(self):
        """Test Entity confidence score validation."""
        # Valid confidence scores
        entity1 = Entity(id="1", name="Test", entity_type="person", confidence_score=0.0)
        assert entity1.confidence_score == 0.0
        
        entity2 = Entity(id="2", name="Test", entity_type="person", confidence_score=1.0)
        assert entity2.confidence_score == 1.0
        
        entity3 = Entity(id="3", name="Test", entity_type="person", confidence_score=0.5)
        assert entity3.confidence_score == 0.5
    
    def test_entity_dict_serialization(self):
        """Test Entity serialization to dict."""
        entity = Entity(
            id="entity-123",
            name="Test Entity",
            entity_type="person",
            properties={"age": 30},
            aliases=["alias1"]
        )
        
        entity_dict = entity.dict()
        assert entity_dict["id"] == "entity-123"
        assert entity_dict["name"] == "Test Entity"
        assert entity_dict["entity_type"] == "person"
        assert entity_dict["properties"]["age"] == 30
        assert entity_dict["aliases"] == ["alias1"]


class TestRelationship:
    """Test cases for Relationship model."""
    
    def test_relationship_creation(self):
        """Test creating a Relationship instance."""
        relationship = Relationship(
            id="rel-123",
            source_entity_id="entity-1",
            target_entity_id="entity-2",
            relationship_type="works_for",
            document_id="doc-123",
            properties={"since": "2020"},
            confidence_score=0.8,
            created_at=datetime.utcnow()
        )
        
        assert relationship.id == "rel-123"
        assert relationship.source_entity_id == "entity-1"
        assert relationship.target_entity_id == "entity-2"
        assert relationship.relationship_type == "works_for"
        assert relationship.document_id == "doc-123"
        assert relationship.properties == {"since": "2020"}
        assert relationship.confidence_score == 0.8
        assert isinstance(relationship.created_at, datetime)
    
    def test_relationship_optional_fields(self):
        """Test Relationship with optional fields."""
        relationship = Relationship(
            id="rel-123",
            source_entity_id="entity-1",
            target_entity_id="entity-2",
            relationship_type="mentions"
        )
        
        assert relationship.document_id is None
        assert relationship.properties == {}
        assert relationship.confidence_score == 0.0
        assert isinstance(relationship.created_at, datetime)
    
    def test_relationship_confidence_score_validation(self):
        """Test Relationship confidence score validation."""
        # Valid confidence scores
        rel1 = Relationship(
            id="1", source_entity_id="e1", target_entity_id="e2", 
            relationship_type="mentions", confidence_score=0.0
        )
        assert rel1.confidence_score == 0.0
        
        rel2 = Relationship(
            id="2", source_entity_id="e1", target_entity_id="e2", 
            relationship_type="mentions", confidence_score=1.0
        )
        assert rel2.confidence_score == 1.0
    
    def test_relationship_dict_serialization(self):
        """Test Relationship serialization to dict."""
        relationship = Relationship(
            id="rel-123",
            source_entity_id="entity-1",
            target_entity_id="entity-2",
            relationship_type="works_for",
            properties={"department": "engineering"}
        )
        
        rel_dict = relationship.dict()
        assert rel_dict["id"] == "rel-123"
        assert rel_dict["source_entity_id"] == "entity-1"
        assert rel_dict["target_entity_id"] == "entity-2"
        assert rel_dict["relationship_type"] == "works_for"
        assert rel_dict["properties"]["department"] == "engineering"


class TestModelIntegration:
    """Test cases for model integration."""
    
    def test_entity_relationship_linkage(self):
        """Test that entities and relationships can be properly linked."""
        entity1 = Entity(
            id="person-1",
            name="John Doe",
            entity_type="person"
        )
        
        entity2 = Entity(
            id="company-1", 
            name="Acme Corp",
            entity_type="organization"
        )
        
        relationship = Relationship(
            id="rel-1",
            source_entity_id=entity1.id,
            target_entity_id=entity2.id,
            relationship_type="works_for"
        )
        
        assert relationship.source_entity_id == entity1.id
        assert relationship.target_entity_id == entity2.id
    
    def test_document_entity_linkage(self):
        """Test that entities can be linked to documents."""
        document = Document(
            id="doc-1",
            title="Company Report",
            content="John Doe works for Acme Corp.",
            source_system="test",
            source_path="/test.txt",
            document_type="txt"
        )
        
        entity = Entity(
            id="entity-1",
            name="John Doe",
            entity_type="person",
            document_id=document.id
        )
        
        assert entity.document_id == document.id
    
    def test_model_json_compatibility(self):
        """Test that models can be serialized to JSON-compatible formats."""
        document = Document(
            id="doc-1",
            title="Test",
            content="Content",
            source_system="test",
            source_path="/test.txt",
            document_type="txt",
            metadata={"nested": {"key": "value"}}
        )
        
        entity = Entity(
            id="entity-1",
            name="Test Entity",
            entity_type="person",
            document_id=document.id,
            properties={"complex": {"data": [1, 2, 3]}}
        )
        
        relationship = Relationship(
            id="rel-1",
            source_entity_id="entity-1",
            target_entity_id="entity-2",
            relationship_type="mentions",
            document_id=document.id,
            properties={"score": 0.95}
        )
        
        # Test that all models can be converted to dict (JSON-compatible)
        doc_dict = document.dict()
        entity_dict = entity.dict()
        rel_dict = relationship.dict()
        
        assert isinstance(doc_dict, dict)
        assert isinstance(entity_dict, dict)
        assert isinstance(rel_dict, dict)
        
        # Test that nested structures are preserved
        assert doc_dict["metadata"]["nested"]["key"] == "value"
        assert entity_dict["properties"]["complex"]["data"] == [1, 2, 3]
        assert rel_dict["properties"]["score"] == 0.95
