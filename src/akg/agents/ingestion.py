"""
Local file ingestion agent for processing documents from the file system.
"""

import asyncio
import fnmatch
import hashlib
import logging
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from ..config import config
from ..database import neo4j_manager, supabase_manager
from ..models import Document
from ..parsers.document_parser import DocumentParser

logger = logging.getLogger(__name__)

class DocumentFileHandler(FileSystemEventHandler):
    """File system event handler for document watching."""
    
    def __init__(self, ingestion_agent):
        self.ingestion_agent = ingestion_agent
        
    def on_created(self, event):
        if not event.is_directory:
            asyncio.create_task(self.ingestion_agent.process_file(event.src_path))
            
    def on_modified(self, event):
        if not event.is_directory:
            asyncio.create_task(self.ingestion_agent.process_file(event.src_path))

class LocalFileIngestionAgent:
    """Agent responsible for ingesting documents from local file system."""
    
    def __init__(self, supabase_manager=None, neo4j_manager=None):
        self.input_dir = Path(config.documents_input_dir)
        self.supported_extensions = config.supported_extensions
        self.exclude_patterns = config.exclude_patterns_list
        self.recursive = config.recursive_scan
        self.watch_enabled = config.watch_directory
        self.processed_files: Dict[str, str] = {}  # file_path -> file_hash
        self.observer = None  # Will be set to Observer() when needed
        self.document_parser = DocumentParser()
        self.supabase_manager = supabase_manager
        self.neo4j_manager = neo4j_manager
        
    async def initialize(self):
        """Initialize the ingestion agent."""
        # Initialize database connections if available
        if self.supabase_manager:
            await self.supabase_manager.initialize()
            await self.supabase_manager.initialize_schema()
        
        if self.neo4j_manager:
            try:
                await self.neo4j_manager.initialize()
            except Exception as e:
                logger.warning(f"Neo4j not available: {e}")
        
        # Create input directory if it doesn't exist
        self.input_dir.mkdir(parents=True, exist_ok=True)
        
        # Start file watching if enabled
        if self.watch_enabled:
            await self.start_watching()
            
        logger.info(f"Local file ingestion agent initialized. Watching: {self.input_dir}")
        
    async def start_watching(self):
        """Start watching the input directory for file changes."""
        if self.observer is None:
            self.observer = Observer()
            event_handler = DocumentFileHandler(self)
            self.observer.schedule(
                event_handler, 
                str(self.input_dir), 
                recursive=self.recursive
            )
            self.observer.start()
            logger.info(f"Started watching directory: {self.input_dir}")
            
    async def stop_watching(self):
        """Stop watching the input directory."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Stopped watching directory")
            
    def _is_excluded(self, file_path: Path) -> bool:
        """Check if file should be excluded based on patterns."""
        relative_path = file_path.relative_to(self.input_dir)
        
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(str(relative_path), pattern):
                return True
                
        return False
        
    def _is_supported(self, file_path: Path) -> bool:
        """Check if file type is supported."""
        return file_path.suffix.lower() in self.supported_extensions
        
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file for change detection."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return ""
            
    def _has_file_changed(self, file_path: Path) -> bool:
        """Check if file has changed since last processing."""
        file_str = str(file_path)
        current_hash = self._calculate_file_hash(file_path)
        
        if file_str not in self.processed_files:
            self.processed_files[file_str] = current_hash
            return True
            
        if self.processed_files[file_str] != current_hash:
            self.processed_files[file_str] = current_hash
            return True
            
        return False
        
    def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from file."""
        stat = file_path.stat()
        
        metadata = {
            "file_size": stat.st_size,
            "created_time": datetime.fromtimestamp(stat.st_ctime),
            "modified_time": datetime.fromtimestamp(stat.st_mtime),
            "file_extension": file_path.suffix.lower(),
            "mime_type": mimetypes.guess_type(str(file_path))[0],
            "relative_path": str(file_path.relative_to(self.input_dir)),
            "absolute_path": str(file_path.absolute())
        }
        
        return metadata
        
    async def scan_directory(self) -> List[Path]:
        """Scan directory for supported documents."""
        files = []
        
        if self.recursive:
            pattern = "**/*"
        else:
            pattern = "*"
            
        for file_path in self.input_dir.glob(pattern):
            if file_path.is_file():
                if self._is_supported(file_path) and not self._is_excluded(file_path):
                    files.append(file_path)
                    
        logger.info(f"Found {len(files)} supported files in {self.input_dir}")
        return files
        
    async def process_file(self, file_path: str) -> Optional[Document]:
        """Process a single file into a Document object."""
        path_obj = Path(file_path)
        
        # Check if file exists and is supported
        if not path_obj.exists():
            logger.warning(f"File does not exist: {path_obj}")
            return None
            
        if not self._is_supported(path_obj):
            logger.debug(f"Unsupported file type: {path_obj}")
            return None
            
        if self._is_excluded(path_obj):
            logger.debug(f"File excluded by patterns: {path_obj}")
            return None
            
        # Check if file has changed
        if not self._has_file_changed(path_obj):
            logger.debug(f"File unchanged, skipping: {path_obj}")
            return None
            
        try:
            # Check if document already exists in database
            existing_doc = None
            if self.supabase_manager:
                try:
                    existing_doc = await self.supabase_manager.get_document_by_path(str(path_obj))
                except Exception as e:
                    logger.warning(f"⚠️ Supabase lookup failed (SSL issue), continuing without check: {e}")
                    existing_doc = None
            
            if existing_doc and not self._has_file_changed(path_obj):
                logger.debug(f"Document already processed and unchanged: {path_obj}")
                return None
            
            # Read file content using enhanced parser
            content = await self.document_parser.parse_document(path_obj)
            
            # Extract metadata
            metadata = self._extract_metadata(path_obj)
            
            # Add parser metadata
            parser_metadata = self.document_parser.get_document_metadata(path_obj, content)
            metadata.update(parser_metadata)
            
            # Ensure metadata is JSON serializable
            json_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, datetime):
                    json_metadata[key] = value.isoformat()
                else:
                    json_metadata[key] = value
            
            # Create document object
            document = Document(
                id=self._generate_document_id(path_obj),
                title=path_obj.stem,
                content=content,
                source_system="local_filesystem",
                source_path=str(path_obj),
                document_type=path_obj.suffix.lower().lstrip('.'),
                metadata=json_metadata,
                processed_at=datetime.utcnow()
            )
            
            # Save to Supabase if available
            if self.supabase_manager:
                try:
                    db_result = await self.supabase_manager.create_document(
                        source_path=document.source_path,
                        content=document.content,
                        document_type=document.document_type,
                        file_size=metadata.get('file_size'),
                        file_hash=metadata.get('file_hash'),
                        metadata=document.metadata
                    )
                    
                    if db_result:
                        logger.info(f"✅ Processed and saved document to Supabase: {path_obj}")
                    else:
                        logger.warning(f"⚠️ Document processed but failed to save to Supabase: {path_obj}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Supabase save failed (SSL issue): {e}")
                    logger.info(f"📄 Document processed locally: {path_obj}")
                
                # Also create a document node in Neo4j if available
                if self.neo4j_manager:
                    try:
                        # Filter metadata to only include primitive types for Neo4j
                        simple_metadata = {}
                        if document.metadata:
                            for key, value in document.metadata.items():
                                if isinstance(value, (str, int, float, bool)):
                                    simple_metadata[key] = value
                                elif isinstance(value, list) and all(isinstance(item, (str, int, float, bool)) for item in value):
                                    simple_metadata[key] = value
                        
                        await self.neo4j_manager.create_document_node(
                            document_id=document.id,
                            source_path=document.source_path,
                            document_type=document.document_type,
                            title=document.title,
                            metadata=simple_metadata if simple_metadata else None
                        )
                        logger.info(f"✅ Document node created in Neo4j: {path_obj}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to create Neo4j document node: {e}")
                
                return document
            else:
                # No database available, just return the document
                logger.info(f"📄 Processed document (no database): {path_obj}")
                return document
            
        except Exception as e:
            logger.error(f"Error processing file {path_obj}: {e}")
            return None
            
    def _generate_document_id(self, file_path: Path) -> str:
        """Generate unique document ID."""
        relative_path = file_path.relative_to(self.input_dir)
        return hashlib.md5(str(relative_path).encode()).hexdigest()
        
    async def process_all_files(self) -> List[Document]:
        """Process all files in the input directory."""
        files = await self.scan_directory()
        documents = []
        
        for file_path in files:
            document = await self.process_file(str(file_path))
            if document:
                documents.append(document)
                
        logger.info(f"Processed {len(documents)} documents from {len(files)} files")
        return documents
        
    async def cleanup(self):
        """Cleanup resources."""
        await self.stop_watching()
