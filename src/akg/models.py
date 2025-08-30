"""
Core data models for the AKG system.
Documents are stored in Supabase, entities and relationships in Neo4j.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Import database types
from .types import EntityType, RelationType


class Document(BaseModel):
    """Represents a source document being processed."""
    id: str
    title: str
    content: str
    source_system: str = "local_files"
    source_path: str
    document_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Entity(BaseModel):
    """Represents an entity extracted from documents."""
    id: str
    name: str
    entity_type: str  # Changed from EntityType to str for flexibility
    document_id: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    aliases: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Relationship(BaseModel):
    """Represents a relationship between entities."""
    id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: str  # Changed from RelationType to str for flexibility
    document_id: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExtractionResult(BaseModel):
    """Results from document processing."""
    document_id: str
    entities: List[Entity] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    processing_time: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
