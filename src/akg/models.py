"""
Core data models for the AKG system.
These models are now stored in Supabase instead of being static.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Import database types and manager
from .database import EntityType, RelationType, db


# Legacy models for compatibility - data is now stored in Supabase
class Document(BaseModel):
    """Represents a source document being processed."""
    id: str
    title: str
    content: str
    source_system: str
    source_path: str
    document_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    async def save_to_db(self) -> Dict[str, Any]:
        """Save document to Supabase."""
        return await db.create_document({
            'title': self.title,
            'content': self.content,
            'source_system': self.source_system,
            'source_path': self.source_path,
            'document_type': self.document_type,
            'metadata': self.metadata,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        })

class Entity(BaseModel):
    """Represents an entity extracted from documents."""
    id: str
    name: str
    entity_type: EntityType
    document_id: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    aliases: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    async def save_to_db(self) -> Dict[str, Any]:
        """Save entity to Supabase."""
        return await db.create_entity({
            'document_id': self.document_id,
            'name': self.name,
            'entity_type': self.entity_type.value,
            'properties': self.properties,
            'aliases': self.aliases,
            'confidence_score': self.confidence_score
        })

class Relationship(BaseModel):
    """Represents a relationship between two entities."""
    id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: RelationType
    document_id: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    async def save_to_db(self) -> Dict[str, Any]:
        """Save relationship to Supabase."""
        return await db.create_relationship({
            'document_id': self.document_id,
            'source_entity_id': self.source_entity_id,
            'target_entity_id': self.target_entity_id,
            'relationship_type': self.relationship_type.value,
            'properties': self.properties,
            'confidence_score': self.confidence_score
        })

class Provenance(BaseModel):
    """Provenance information for tracking data lineage."""
    document_id: str
    document_title: Optional[str] = None
    source_system: str
    extraction_timestamp: datetime
    confidence_score: float = Field(ge=0.0, le=1.0)
    page_number: Optional[int] = None
    paragraph_index: Optional[int] = None
    extractor_version: str = "1.0"
    
    async def save_to_db(self, entity_id: Optional[str] = None, relationship_id: Optional[str] = None) -> Dict[str, Any]:
        """Save provenance to Supabase."""
        return await db.create_provenance({
            'document_id': self.document_id,
            'entity_id': entity_id,
            'relationship_id': relationship_id,
            'source_system': self.source_system,
            'extraction_timestamp': self.extraction_timestamp.isoformat(),
            'confidence_score': self.confidence_score,
            'page_number': self.page_number,
            'paragraph_index': self.paragraph_index,
            'extractor_version': self.extractor_version
        })

class ExtractionResult(BaseModel):
    """Results from entity and relationship extraction."""
    document_id: str
    entities: List[Entity] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict)
    processing_time: float
    success: bool = True
    error_message: Optional[str] = None
    
    async def save_to_db(self) -> Dict[str, Any]:
        """Save extraction result to Supabase."""
        # Save entities and relationships first
        saved_entities = []
        saved_relationships = []
        
        for entity in self.entities:
            entity.document_id = self.document_id
            saved_entity = await entity.save_to_db()
            saved_entities.append(saved_entity)
            
        for relationship in self.relationships:
            relationship.document_id = self.document_id
            saved_relationship = await relationship.save_to_db()
            saved_relationships.append(saved_relationship)
            
        # Save extraction result summary
        return await db.supabase.table('extraction_results').insert({
            'document_id': self.document_id,
            'processing_time': self.processing_time,
            'success': self.success,
            'error_message': self.error_message,
            'extraction_metadata': self.extraction_metadata,
            'entities_count': len(saved_entities),
            'relationships_count': len(saved_relationships)
        }).execute()

class ConflictResolution(BaseModel):
    """Represents a conflict that needs resolution."""
    id: str
    conflict_type: str
    description: str
    conflicting_entities: List[str] = Field(default_factory=list)
    conflicting_relationships: List[str] = Field(default_factory=list)
    resolution_strategy: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    human_review_required: bool = False

class QueryResult(BaseModel):
    """Results from knowledge graph queries."""
    query: str
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    paths: List[List[str]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    execution_time: float
    total_results: int
