"""
Configuration management for AKG system.
"""

import os
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# Load environment variables
load_dotenv()

class AKGConfig(BaseSettings):
    """Application configuration with environment variable support."""
    
    # Google Gemini Configuration
    google_api_key: str = Field(..., alias="GOOGLE_API_KEY")
    google_project_id: Optional[str] = Field(None, alias="GOOGLE_PROJECT_ID")
    
    # LlamaParse Configuration
    llama_cloud_api_key: str = Field(..., alias="LLAMA_CLOUD_API_KEY")
    
    # Neo4j Configuration
    neo4j_uri: str = Field("bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_username: str = Field("neo4j", alias="NEO4J_USERNAME")
    neo4j_password: str = Field(..., alias="NEO4J_PASSWORD")
    neo4j_database: str = Field("neo4j", alias="NEO4J_DATABASE")
    
    # Supabase Configuration
    supabase_url: str = Field(..., alias="SUPABASE_URL")
    supabase_api_key: str = Field(..., alias="SUPABASE_API_KEY")
    supabase_service_role_key: Optional[str] = Field(None, alias="SUPABASE_SERVICE_ROLE_KEY")
    
    # Application Settings
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    max_concurrent_documents: int = Field(5, alias="MAX_CONCURRENT_DOCUMENTS")
    chunk_size: int = Field(1000, alias="CHUNK_SIZE")
    overlap_size: int = Field(200, alias="OVERLAP_SIZE")
    
    # Graph Configuration
    max_graph_depth: int = Field(5, alias="MAX_GRAPH_DEPTH")
    similarity_threshold: float = Field(0.8, alias="SIMILARITY_THRESHOLD")
    provenance_enabled: bool = Field(True, alias="PROVENANCE_ENABLED")
    
    # Entity Deduplication Configuration
    enable_entity_deduplication: bool = Field(True, alias="ENABLE_ENTITY_DEDUPLICATION")
    entity_similarity_threshold: float = Field(0.8, alias="ENTITY_SIMILARITY_THRESHOLD")
    cross_type_similarity_threshold: float = Field(0.95, alias="CROSS_TYPE_SIMILARITY_THRESHOLD")
    enable_relationship_deduplication: bool = Field(True, alias="ENABLE_RELATIONSHIP_DEDUPLICATION")
    
    # Local File Ingestion Configuration
    documents_input_dir: str = Field("./documents", alias="DOCUMENTS_INPUT_DIR")
    supported_file_types: str = Field("pdf,docx,txt,md,html,pptx,xlsx", alias="SUPPORTED_FILE_TYPES")
    watch_directory: bool = Field(True, alias="WATCH_DIRECTORY")
    recursive_scan: bool = Field(True, alias="RECURSIVE_SCAN")
    exclude_patterns: str = Field(".git/*,node_modules/*,__pycache__/*", alias="EXCLUDE_PATTERNS")
    
    # Optional integrations (disabled for local mode)
    sharepoint_client_id: Optional[str] = Field(None, alias="SHAREPOINT_CLIENT_ID")
    sharepoint_client_secret: Optional[str] = Field(None, alias="SHAREPOINT_CLIENT_SECRET")
    sharepoint_tenant_id: Optional[str] = Field(None, alias="SHAREPOINT_TENANT_ID")
    
    confluence_url: Optional[str] = Field(None, alias="CONFLUENCE_URL")
    confluence_username: Optional[str] = Field(None, alias="CONFLUENCE_USERNAME")
    confluence_api_token: Optional[str] = Field(None, alias="CONFLUENCE_API_TOKEN")
    
    jira_url: Optional[str] = Field(None, alias="JIRA_URL")
    jira_username: Optional[str] = Field(None, alias="JIRA_USERNAME")
    jira_api_token: Optional[str] = Field(None, alias="JIRA_API_TOKEN")
    
    @property
    def supported_extensions(self) -> set:
        """Get supported file extensions as a set."""
        return {f".{ext.strip()}" for ext in self.supported_file_types.split(",")}
    
    @property
    def exclude_patterns_list(self) -> list:
        """Get exclude patterns as a list."""
        return [pattern.strip() for pattern in self.exclude_patterns.split(",")]
    
    model_config = {"env_file": ".env", "case_sensitive": False}

# Global configuration instance
config = AKGConfig()
