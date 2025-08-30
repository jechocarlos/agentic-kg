"""
Supabase manager for document storage and metadata only.
Entities and relationships are handled by Neo4j.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from supabase import Client, create_client

from ..config import config


class SupabaseManager:
    """Manager for Supabase document storage operations."""
    
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
        # Check if tables exist by trying to query them
        try:
            self.supabase.table('documents').select('id').limit(1).execute()
        except Exception:
            # Tables don't exist, we should create them via SQL or migrations
            print("Tables need to be created in Supabase. Please run the provided SQL script.")
            
    async def create_document(self, title: str, content: str, source_path: str, 
                            document_type: str, file_size: int = None, 
                            file_hash: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new document record."""
        document_data = {
            'id': str(uuid.uuid4()),
            'title': title,
            'content': content,
            'source_path': source_path,
            'document_type': document_type,
            'file_size': file_size,
            'file_hash': file_hash,
            'metadata': metadata or {},
            'processing_status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        result = self.supabase.table('documents').insert(document_data).execute()
        return result.data[0] if result.data else None
        
    async def get_document_by_path(self, source_path: str) -> Optional[Dict[str, Any]]:
        """Get document by source path."""
        result = self.supabase.table('documents').select('*').eq('source_path', source_path).execute()
        return result.data[0] if result.data else None
        
    async def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        result = self.supabase.table('documents').select('*').eq('id', document_id).execute()
        return result.data[0] if result.data else None
        
    async def update_document_status(self, document_id: str, status: str, 
                                   error_message: str = None) -> bool:
        """Update document processing status."""
        update_data = {
            'processing_status': status,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if status == 'completed':
            update_data['processed_at'] = datetime.utcnow().isoformat()
        elif error_message:
            update_data['error_message'] = error_message
            
        result = self.supabase.table('documents').update(update_data).eq('id', document_id).execute()
        return len(result.data) > 0
        
    async def create_extraction_job(self, document_id: str, 
                                  metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create an extraction job record."""
        job_data = {
            'id': str(uuid.uuid4()),
            'document_id': document_id,
            'status': 'pending',
            'extraction_metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = self.supabase.table('extraction_jobs').insert(job_data).execute()
        return result.data[0] if result.data else None
        
    async def update_extraction_job(self, job_id: str, status: str, 
                                  entities_count: int = 0, relationships_count: int = 0,
                                  processing_time: float = None, error_message: str = None) -> bool:
        """Update extraction job with results."""
        update_data = {
            'status': status,
            'entities_extracted': entities_count,
            'relationships_extracted': relationships_count,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if status in ['completed', 'failed']:
            update_data['completed_at'] = datetime.utcnow().isoformat()
            
        if processing_time is not None:
            update_data['processing_time_seconds'] = processing_time
            
        if error_message:
            update_data['error_message'] = error_message
            
        result = self.supabase.table('extraction_jobs').update(update_data).eq('id', job_id).execute()
        return len(result.data) > 0
        
    async def get_documents(self, limit: int = 100, offset: int = 0, 
                          status: str = None) -> List[Dict[str, Any]]:
        """Get documents with optional filtering."""
        query = self.supabase.table('documents').select('*')
        
        if status:
            query = query.eq('processing_status', status)
            
        query = query.order('created_at', desc=True).range(offset, offset + limit - 1)
        result = query.execute()
        
        return result.data or []
        
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        try:
            result = self.supabase.table('processing_stats').select('*').execute()
            if result.data:
                return result.data[0]
        except Exception:
            pass
            
        # Fallback: calculate stats manually
        docs_result = self.supabase.table('documents').select('processing_status').execute()
        docs = docs_result.data or []
        
        stats = {
            'total_documents': len(docs),
            'completed_documents': len([d for d in docs if d['processing_status'] == 'completed']),
            'failed_documents': len([d for d in docs if d['processing_status'] == 'failed']),
            'pending_documents': len([d for d in docs if d['processing_status'] == 'pending']),
            'total_entities_extracted': 0,  # Will be calculated from Neo4j
            'total_relationships_extracted': 0,  # Will be calculated from Neo4j
        }
        
        return stats
        
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and all related records."""
        try:
            # Delete extraction jobs first
            self.supabase.table('extraction_jobs').delete().eq('document_id', document_id).execute()
            
            # Delete document chunks
            self.supabase.table('document_chunks').delete().eq('document_id', document_id).execute()
            
            # Delete the document
            result = self.supabase.table('documents').delete().eq('id', document_id).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False
            
    async def log_system_event(self, level: str, message: str, component: str = None,
                             document_id: str = None, metadata: Dict[str, Any] = None):
        """Log a system event."""
        log_data = {
            'id': str(uuid.uuid4()),
            'level': level,
            'message': message,
            'component': component,
            'document_id': document_id,
            'metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat()
        }
        
        try:
            self.supabase.table('system_logs').insert(log_data).execute()
        except Exception as e:
            print(f"Error logging system event: {e}")
            
    async def get_document_summary(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document summary with processing information."""
        try:
            result = self.supabase.table('document_processing_summary').select('*').eq('id', document_id).execute()
            return result.data[0] if result.data else None
        except Exception:
            # Fallback to basic document info
            return await self.get_document_by_id(document_id)
