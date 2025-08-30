"""
Supabase manager for document storage and metadata only.
Entities and relationships are handled by Neo4j.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from supabase import Client, create_client

logger = logging.getLogger(__name__)


class SupabaseManager:
    """Manager for Supabase document storage operations."""
    
    def __init__(self, url: str, key: str):
        self.url = url
        self.key = key
        self.client: Optional[Client] = None
        
    async def initialize(self):
        """Initialize Supabase client"""
        try:
            # Disable SSL verification for macOS certificate issues
            os.environ['PYTHONHTTPSVERIFY'] = '0'
            
            self.client = create_client(self.url, self.key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
        
    async def initialize_schema(self):
        """Initialize database schema with required tables."""
        # This would typically be done via Supabase migrations
        # For now, we'll check if tables exist and create them if needed
        await self._ensure_tables_exist()
        
    async def _ensure_tables_exist(self):
        """Ensure all required tables exist in Supabase."""
        # Check if tables exist by trying to query them
        try:
            if self.client:
                self.client.table('documents').select('id').limit(1).execute()
        except Exception:
            # Tables don't exist, we should create them via SQL or migrations
            logger.warning("Database tables may not exist. Please run the schema migration.")
    
    async def create_document(self, source_path: str, content: str,
                            document_type: str, file_size: Optional[int] = None,
                            file_hash: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Create a new document record in Supabase."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
            
        document_data = {
            'id': str(uuid.uuid4()),
            'source_path': source_path,
            'content': content,
            'document_type': document_type,
            'file_size': file_size,
            'file_hash': file_hash,
            'metadata': json.dumps(metadata) if metadata else None,
            'status': 'uploaded',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        result = self.client.table('documents').insert(document_data).execute()
        return result.data[0] if result.data else None
    
    async def get_document_by_path(self, source_path: str) -> Optional[Dict[str, Any]]:
        """Get document by source path."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        result = self.client.table('documents').select('*').eq('source_path', source_path).execute()
        return result.data[0] if result.data else None
    
    async def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        result = self.client.table('documents').select('*').eq('id', document_id).execute()
        return result.data[0] if result.data else None
    
    async def update_document_status(self, document_id: str, status: str,
                                   error_message: Optional[str] = None) -> bool:
        """Update document processing status."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
            
        update_data = {
            'status': status,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if error_message:
            update_data['error_message'] = error_message
            
        result = self.client.table('documents').update(update_data).eq('id', document_id).execute()
        return len(result.data) > 0
    
    async def create_extraction_job(self, document_id: str,
                                  metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Create a new extraction job."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
            
        job_data = {
            'id': str(uuid.uuid4()),
            'document_id': document_id,
            'status': 'pending',
            'metadata': json.dumps(metadata) if metadata else None,
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = self.client.table('extraction_jobs').insert(job_data).execute()
        return result.data[0] if result.data else None
    
    async def update_extraction_job(self, job_id: str, status: str,
                                  processing_time: Optional[float] = None, error_message: Optional[str] = None) -> bool:
        """Update extraction job status."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
            
        update_data = {
            'status': status,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if processing_time is not None:
            update_data['processing_time'] = str(processing_time)
            
        if error_message:
            update_data['error_message'] = error_message
            
        result = self.client.table('extraction_jobs').update(update_data).eq('id', job_id).execute()
        return len(result.data) > 0
    
    async def get_documents(self, limit: int = 100, offset: int = 0,
                          status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of documents with optional filtering."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        query = self.client.table('documents').select('*')
        
        if status:
            query = query.eq('status', status)
            
        query = query.range(offset, offset + limit - 1)
        result = query.execute()
        return result.data
    
    async def get_document_stats(self) -> Dict[str, int]:
        """Get document statistics."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
            
        # Get total documents
        total_result = self.client.table('documents').select('*').execute()
        total_count = len(total_result.data) if total_result.data else 0
        
        # Get documents by status
        uploaded_result = self.client.table('documents').select('*').eq('status', 'uploaded').execute()
        uploaded_count = len(uploaded_result.data) if uploaded_result.data else 0
        
        processed_result = self.client.table('documents').select('*').eq('status', 'processed').execute()
        processed_count = len(processed_result.data) if processed_result.data else 0
        
        failed_result = self.client.table('documents').select('*').eq('status', 'failed').execute()
        failed_count = len(failed_result.data) if failed_result.data else 0
        
        return {
            'total': total_count,
            'uploaded': uploaded_count,
            'processed': processed_count,
            'failed': failed_count
        }
    
    async def store_document_chunks(self, document_id: str, chunks: List[Dict[str, Any]]) -> bool:
        """Store document chunks for processing."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
            
        chunk_data = []
        for i, chunk in enumerate(chunks):
            chunk_data.append({
                'id': str(uuid.uuid4()),
                'document_id': document_id,
                'chunk_index': i,
                'content': chunk.get('content', ''),
                'metadata': json.dumps(chunk.get('metadata', {})),
                'created_at': datetime.utcnow().isoformat()
            })
        
        result = self.client.table('document_chunks').insert(chunk_data).execute()
        return len(result.data) > 0
    
    async def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """Get chunks for a document."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        result = self.client.table('document_chunks').select('*').eq('document_id', document_id).order('chunk_index').execute()
        return result.data
    
    async def log_system_event(self, event_type: str, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log system events."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
            
        log_data = {
            'id': str(uuid.uuid4()),
            'event_type': event_type,
            'message': message,
            'metadata': json.dumps(metadata) if metadata else None,
            'created_at': datetime.utcnow().isoformat()
        }
        
        try:
            self.client.table('system_logs').insert(log_data).execute()
        except Exception as e:
            logger.error(f"Failed to log system event: {e}")
    
    # Domain-specific type management methods
    
    async def store_domain_entity_type(self, domain: str, entity_type: str, 
                                     subdomain: Optional[str] = None,
                                     description: Optional[str] = None,
                                     confidence_score: float = 0.0,
                                     source: str = 'document_analysis',
                                     metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store or update a domain-specific entity type."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        
        # Check if type already exists
        existing = self.client.table('domain_entity_types').select('*').eq('domain', domain).eq('entity_type', entity_type)
        if subdomain:
            existing = existing.eq('subdomain', subdomain)
        else:
            existing = existing.is_('subdomain', 'null')
        
        existing_result = existing.execute()
        
        if existing_result.data:
            # Update existing record (increment usage count)
            existing_record = existing_result.data[0]
            update_data = {
                'usage_count': existing_record['usage_count'] + 1,
                'confidence_score': max(existing_record['confidence_score'], confidence_score),
                'updated_at': datetime.utcnow().isoformat()
            }
            if description and not existing_record['description']:
                update_data['description'] = description
            if metadata:
                update_data['metadata'] = json.dumps(metadata)
            
            result = self.client.table('domain_entity_types').update(update_data).eq('id', existing_record['id']).execute()
            return len(result.data) > 0
        else:
            # Insert new record
            insert_data = {
                'domain': domain,
                'subdomain': subdomain,
                'entity_type': entity_type,
                'description': description,
                'usage_count': 1,
                'confidence_score': confidence_score,
                'source': source,
                'metadata': json.dumps(metadata) if metadata else None
            }
            
            result = self.client.table('domain_entity_types').insert(insert_data).execute()
            return len(result.data) > 0
    
    async def store_domain_relationship_type(self, domain: str, relationship_type: str,
                                           source_verb: Optional[str] = None,
                                           subdomain: Optional[str] = None,
                                           description: Optional[str] = None,
                                           confidence_score: float = 0.0,
                                           source: str = 'document_analysis',
                                           metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store or update a domain-specific relationship type."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        
        # Check if type already exists
        existing = self.client.table('domain_relationship_types').select('*').eq('domain', domain).eq('relationship_type', relationship_type)
        if subdomain:
            existing = existing.eq('subdomain', subdomain)
        else:
            existing = existing.is_('subdomain', 'null')
        
        existing_result = existing.execute()
        
        if existing_result.data:
            # Update existing record (increment usage count)
            existing_record = existing_result.data[0]
            update_data = {
                'usage_count': existing_record['usage_count'] + 1,
                'confidence_score': max(existing_record['confidence_score'], confidence_score),
                'updated_at': datetime.utcnow().isoformat()
            }
            if description and not existing_record['description']:
                update_data['description'] = description
            if source_verb and not existing_record['source_verb']:
                update_data['source_verb'] = source_verb
            if metadata:
                update_data['metadata'] = json.dumps(metadata)
            
            result = self.client.table('domain_relationship_types').update(update_data).eq('id', existing_record['id']).execute()
            return len(result.data) > 0
        else:
            # Insert new record
            insert_data = {
                'domain': domain,
                'subdomain': subdomain,
                'relationship_type': relationship_type,
                'source_verb': source_verb,
                'description': description,
                'usage_count': 1,
                'confidence_score': confidence_score,
                'source': source,
                'metadata': json.dumps(metadata) if metadata else None
            }
            
            result = self.client.table('domain_relationship_types').insert(insert_data).execute()
            return len(result.data) > 0
    
    async def get_domain_entity_types(self, domain: str, subdomain: Optional[str] = None,
                                    limit: int = 100) -> List[Dict[str, Any]]:
        """Get entity types for a specific domain."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        
        query = self.client.table('domain_entity_types').select('*').eq('domain', domain)
        if subdomain:
            query = query.eq('subdomain', subdomain)
        
        query = query.order('usage_count', desc=True).order('confidence_score', desc=True).limit(limit)
        result = query.execute()
        return result.data
    
    async def get_domain_relationship_types(self, domain: str, subdomain: Optional[str] = None,
                                          limit: int = 100) -> List[Dict[str, Any]]:
        """Get relationship types for a specific domain."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        
        query = self.client.table('domain_relationship_types').select('*').eq('domain', domain)
        if subdomain:
            query = query.eq('subdomain', subdomain)
        
        query = query.order('usage_count', desc=True).order('confidence_score', desc=True).limit(limit)
        result = query.execute()
        return result.data
    
    async def store_domain_analysis_cache(self, content_hash: str, analysis_data: Dict[str, Any]) -> bool:
        """Cache document analysis results."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        
        cache_data = {
            'content_hash': content_hash,
            'document_type': analysis_data.get('document_type'),
            'domain': analysis_data.get('domain'),
            'subdomain': analysis_data.get('subdomain'),
            'description': analysis_data.get('description'),
            'key_entity_types': json.dumps(analysis_data.get('key_entity_types', [])),
            'key_relationship_types': json.dumps(analysis_data.get('key_relationship_types', [])),
            'structural_elements': json.dumps(analysis_data.get('structural_elements', [])),
            'content_focus': analysis_data.get('content_focus'),
            'confidence': analysis_data.get('confidence', 0.0),
            'analysis_method': analysis_data.get('analysis_method', 'ai_generated'),
            'metadata': json.dumps(analysis_data.get('metadata', {}))
        }
        
        # Use upsert to handle duplicates
        result = self.client.table('domain_analysis_cache').upsert(cache_data, on_conflict='content_hash').execute()
        return len(result.data) > 0
    
    async def get_domain_analysis_cache(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached document analysis results."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        
        result = self.client.table('domain_analysis_cache').select('*').eq('content_hash', content_hash).execute()
        if result.data:
            cached = result.data[0]
            # Parse JSON fields back
            cached['key_entity_types'] = json.loads(cached['key_entity_types'])
            cached['key_relationship_types'] = json.loads(cached['key_relationship_types'])
            cached['structural_elements'] = json.loads(cached['structural_elements'])
            cached['metadata'] = json.loads(cached['metadata']) if cached['metadata'] else {}
            return cached
        return None
    
    async def store_verb_extraction(self, document_id: str, original_verb: str,
                                  normalized_relationship: str, context_snippet: str,
                                  domain: Optional[str] = None, confidence_score: float = 0.0,
                                  extraction_method: str = 'regex',
                                  metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store verb extraction results for analysis."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        
        extraction_data = {
            'document_id': document_id,
            'original_verb': original_verb,
            'normalized_relationship': normalized_relationship,
            'context_snippet': context_snippet[:500],  # Limit context length
            'domain': domain,
            'confidence_score': confidence_score,
            'extraction_method': extraction_method,
            'metadata': json.dumps(metadata) if metadata else None
        }
        
        result = self.client.table('verb_extractions').insert(extraction_data).execute()
        return len(result.data) > 0
    
    async def get_domain_statistics(self) -> Dict[str, Any]:
        """Get statistics about domain-specific types."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        
        # Get domain type statistics
        stats_result = self.client.table('domain_type_statistics').select('*').execute()
        
        # Get total counts
        entity_count = self.client.table('domain_entity_types').select('*').execute()
        relationship_count = self.client.table('domain_relationship_types').select('*').execute()
        verb_count = self.client.table('verb_extractions').select('*').execute()
        
        return {
            'domain_statistics': stats_result.data,
            'total_entity_types': len(entity_count.data) if entity_count.data else 0,
            'total_relationship_types': len(relationship_count.data) if relationship_count.data else 0,
            'total_verb_extractions': len(verb_count.data) if verb_count.data else 0
        }

    async def close(self):
        """Close the Supabase connection."""
        # Supabase doesn't require explicit closing
        self.client = None
        logger.info("Supabase client closed")
