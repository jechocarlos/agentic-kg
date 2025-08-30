"""
Database models and operations using Supabase.
"""

import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field
from supabase import Client, create_client

from ..config import config


class EntityType(str, Enum):
    """Types of entities that can be extracted."""
    PERSON = "person"
    ORGANIZATION = "organization"
    POLICY = "policy"
    PROJECT = "project"
    DOCUMENT = "document"
    MEETING = "meeting"
    DECISION = "decision"
    ROLE = "role"
    LOCATION = "location"
    DATE = "date"
    OTHER = "other"

class RelationType(str, Enum):
    """Types of relationships between entities."""
    APPROVED_BY = "approved_by"
    CREATED_BY = "created_by"
    MENTIONED_IN = "mentioned_in"
    REPORTS_TO = "reports_to"
    WORKS_ON = "works_on"
    PARTICIPATES_IN = "participates_in"
    OWNS = "owns"
    MANAGES = "manages"
    COLLABORATES_WITH = "collaborates_with"
    SUPERSEDES = "supersedes"
    REFERENCES = "references"
    OTHER = "other"

class SupabaseManager:
    """Manager for all Supabase database operations."""
    
    def __init__(self):
        self.supabase: Client = create_client(
            config.supabase_url,
            config.supabase_api_key
        )
        
    async def initialize_schema(self):
        """Initialize database schema with required tables."""
        # This would typically be done via Supabase migrations
        # For now, we'll check if tables exist and create them if needed
        await self._ensure_tables_exist()
        
    async def _ensure_tables_exist(self):
        """Ensure all required tables exist in Supabase."""
        # Note: In production, you should use Supabase migrations
        # This is a simplified approach for development
        
        # Check if tables exist by trying to query them
        try:
            self.supabase.table('documents').select('id').limit(1).execute()
        except Exception:
            # Tables don't exist, we should create them via SQL or migrations
            print("Tables need to be created in Supabase. Please run the provided SQL script.")
            
    async def create_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document record."""
        document_data['id'] = str(uuid.uuid4())
        document_data['created_at'] = datetime.utcnow().isoformat()
        document_data['updated_at'] = datetime.utcnow().isoformat()
        
        result = self.supabase.table('documents').insert(document_data).execute()
        return result.data[0] if result.data else None
        
    async def create_entity(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new entity record."""
        entity_data['id'] = str(uuid.uuid4())
        entity_data['created_at'] = datetime.utcnow().isoformat()
        entity_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Convert properties to JSON string for storage
        if 'properties' in entity_data and isinstance(entity_data['properties'], dict):
            entity_data['properties'] = json.dumps(entity_data['properties'])
            
        result = self.supabase.table('entities').insert(entity_data).execute()
        return result.data[0] if result.data else None
        
    async def create_relationship(self, relationship_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new relationship record."""
        relationship_data['id'] = str(uuid.uuid4())
        relationship_data['created_at'] = datetime.utcnow().isoformat()
        relationship_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Convert properties to JSON string for storage
        if 'properties' in relationship_data and isinstance(relationship_data['properties'], dict):
            relationship_data['properties'] = json.dumps(relationship_data['properties'])
            
        result = self.supabase.table('relationships').insert(relationship_data).execute()
        return result.data[0] if result.data else None
        
    async def create_provenance(self, provenance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new provenance record."""
        provenance_data['id'] = str(uuid.uuid4())
        provenance_data['created_at'] = datetime.utcnow().isoformat()
        
        result = self.supabase.table('provenance').insert(provenance_data).execute()
        return result.data[0] if result.data else None
        
    async def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID."""
        result = self.supabase.table('documents').select('*').eq('id', document_id).execute()
        return result.data[0] if result.data else None
        
    async def get_documents_by_source_path(self, source_path: str) -> List[Dict[str, Any]]:
        """Get documents by source path."""
        result = self.supabase.table('documents').select('*').eq('source_path', source_path).execute()
        return result.data or []
        
    async def get_entities_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all entities extracted from a document."""
        result = (self.supabase.table('entities')
                 .select('*')
                 .eq('document_id', document_id)
                 .execute())
        
        # Parse JSON properties back to dict
        for entity in result.data:
            if entity.get('properties') and isinstance(entity['properties'], str):
                try:
                    entity['properties'] = json.loads(entity['properties'])
                except json.JSONDecodeError:
                    entity['properties'] = {}
                    
        return result.data or []
        
    async def get_relationships_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all relationships extracted from a document."""
        result = (self.supabase.table('relationships')
                 .select('*')
                 .eq('document_id', document_id)
                 .execute())
        
        # Parse JSON properties back to dict
        for relationship in result.data:
            if relationship.get('properties') and isinstance(relationship['properties'], str):
                try:
                    relationship['properties'] = json.loads(relationship['properties'])
                except json.JSONDecodeError:
                    relationship['properties'] = {}
                    
        return result.data or []
        
    async def search_entities_by_name(self, name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search entities by name."""
        result = (self.supabase.table('entities')
                 .select('*')
                 .ilike('name', f'%{name}%')
                 .limit(limit)
                 .execute())
        return result.data or []
        
    async def get_entity_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get all relationships for an entity."""
        # Get relationships where entity is source or target
        source_result = (self.supabase.table('relationships')
                        .select('*')
                        .eq('source_entity_id', entity_id)
                        .execute())
        
        target_result = (self.supabase.table('relationships')
                        .select('*')
                        .eq('target_entity_id', entity_id)
                        .execute())
        
        all_relationships = (source_result.data or []) + (target_result.data or [])
        
        # Remove duplicates based on ID
        seen_ids = set()
        unique_relationships = []
        for rel in all_relationships:
            if rel['id'] not in seen_ids:
                seen_ids.add(rel['id'])
                unique_relationships.append(rel)
                
        return unique_relationships
        
    async def update_entity(self, entity_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an entity."""
        updates['updated_at'] = datetime.utcnow().isoformat()
        
        if 'properties' in updates and isinstance(updates['properties'], dict):
            updates['properties'] = json.dumps(updates['properties'])
            
        result = (self.supabase.table('entities')
                 .update(updates)
                 .eq('id', entity_id)
                 .execute())
        return result.data[0] if result.data else None
        
    async def delete_document_data(self, document_id: str):
        """Delete all data associated with a document."""
        # Delete relationships first (due to foreign key constraints)
        self.supabase.table('relationships').delete().eq('document_id', document_id).execute()
        
        # Delete entities
        self.supabase.table('entities').delete().eq('document_id', document_id).execute()
        
        # Delete provenance
        self.supabase.table('provenance').delete().eq('document_id', document_id).execute()
        
        # Delete document
        self.supabase.table('documents').delete().eq('id', document_id).execute()
        
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        doc_count = self.supabase.table('documents').select('id', count='exact').execute()
        entity_count = self.supabase.table('entities').select('id', count='exact').execute()
        relationship_count = self.supabase.table('relationships').select('id', count='exact').execute()
        
        return {
            'total_documents': doc_count.count,
            'total_entities': entity_count.count,
            'total_relationships': relationship_count.count,
            'last_updated': datetime.utcnow().isoformat()
        }

# Global database manager instance
db = SupabaseManager()
