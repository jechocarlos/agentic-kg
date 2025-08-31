# AKG API Reference

## Core Classes and Methods

### EntityExtractionAgent

**Location**: `src/akg/agents/extraction.py`

The main agent responsible for extracting entities and relationships from documents using AI with intelligent fallbacks.

#### Constructor

```python
def __init__(self, neo4j_manager=None, supabase_manager=None):
    """
    Initialize the extraction agent.
    
    Args:
        neo4j_manager: Neo4jManager instance for graph operations
        supabase_manager: SupabaseManager instance for domain type caching
    """
```

#### Core Methods

##### `extract_entities_and_relationships(document: Document) -> Tuple[List[Entity], List[Relationship]]`

**Primary extraction method that processes a document end-to-end.**

```python
async def extract_entities_and_relationships(
    self, 
    document: Document
) -> Tuple[List[Entity], List[Relationship]]:
    """
    Extract entities and relationships from a document using adaptive processing.
    
    Args:
        document: Document object containing title, content, and metadata
        
    Returns:
        Tuple of (entities, relationships) lists
        
    Process:
        1. Analyze document nature and domain
        2. Refresh type cache from Neo4j
        3. Chunk document for optimal processing
        4. Process each chunk with Gemini AI
        5. Save results immediately to Neo4j
        6. Return aggregated results
        
    Raises:
        Exception: If both AI and fallback extraction fail
    """
```

##### `_analyze_document_nature(document: Document) -> Dict[str, Any]`

**Analyzes document characteristics to optimize extraction strategy.**

```python
async def _analyze_document_nature(self, document: Document) -> Dict[str, Any]:
    """
    Analyze document to determine domain, type, and processing strategy.
    
    Args:
        document: Document to analyze
        
    Returns:
        Dict containing:
        - domain: Primary domain (technical, business, legal, etc.)
        - subdomain: More specific classification
        - description: Analysis summary
        - processing_hints: Extraction optimization hints
        - confidence: Analysis confidence score
        
    Uses Gemini AI to classify documents by:
        - Content type (technical specs, business docs, legal contracts)
        - Domain focus (engineering, finance, legal, etc.)
        - Structural elements (lists, tables, procedures)
        - Entity density and relationship complexity
    """
```

##### `_chunk_document(document: Document) -> List[str]`

**Intelligently splits documents for optimal AI processing.**

```python
def _chunk_document(self, document: Document) -> List[str]:
    """
    Split document into optimal chunks for AI processing.
    
    Args:
        document: Document to chunk
        
    Returns:
        List of text chunks
        
    Strategy:
        - Target chunk size: 2000 characters
        - Overlap size: 200 characters for context
        - Split at sentence boundaries when possible
        - Preserve paragraph structure
        - Maintain context across chunks
        
    Configuration:
        - CHUNK_SIZE: Target chunk size (default: 2000)
        - OVERLAP_SIZE: Overlap between chunks (default: 200)
    """
```

##### `save_to_neo4j(entities: List[Entity], relationships: List[Relationship]) -> bool`

**Saves extracted data to Neo4j with dynamic labeling.**

```python
async def save_to_neo4j(
    self, 
    entities: List[Entity], 
    relationships: List[Relationship]
) -> bool:
    """
    Save entities and relationships to Neo4j graph database.
    
    Args:
        entities: List of Entity objects
        relationships: List of Relationship objects
        
    Returns:
        bool: True if successful, False otherwise
        
    Features:
        - Dynamic node labeling (:Entity:PERSON, :Entity:API)
        - Duplicate detection and merging
        - Relationship type standardization (ALL CAPS)
        - Property normalization
        - Error handling and logging
        
    Process:
        1. Create entities with dynamic labels
        2. Create relationships with standardized types
        3. Update type manager cache
        4. Log statistics and performance metrics
    """
```

---

### Neo4jManager

**Location**: `src/akg/database/neo4j_manager.py`

Manages all Neo4j graph database operations with dynamic labeling support.

#### Constructor

```python
def __init__(self, uri=None, username=None, password=None):
    """
    Initialize Neo4j manager with connection parameters.
    
    Args:
        uri: Neo4j connection URI (default: bolt://localhost:7687)
        username: Database username (default: neo4j)
        password: Database password (required)
    """
```

#### Core Methods

##### `create_entity(entity_id, name, entity_type, document_id, properties, confidence_score) -> bool`

**Creates entity nodes with dynamic labeling.**

```python
async def create_entity(
    self,
    entity_id: str,
    name: str,
    entity_type: str,
    document_id: str,
    properties: Dict[str, Any],
    confidence_score: float
) -> bool:
    """
    Create entity with dynamic Neo4j labels.
    
    Args:
        entity_id: Unique entity identifier
        name: Entity name/title
        entity_type: Type classification (PERSON, API, etc.)
        document_id: Source document ID
        properties: Additional entity properties
        confidence_score: Extraction confidence (0.0-1.0)
        
    Returns:
        bool: Creation success status
        
    Features:
        - Automatic label sanitization (PERSON → :PERSON)
        - Dual labeling (:Entity + :PERSON for backward compatibility)
        - Property normalization and validation
        - Duplicate detection
        
    Labels Created:
        - Base label: :Entity
        - Type label: :PERSON, :API, :DATABASE, etc.
        - Combined: :Entity:PERSON
    """
```

##### `create_relationship(rel_id, source_id, target_id, rel_type, document_id, properties, confidence_score) -> bool`

**Creates relationships with standardized types.**

```python
async def create_relationship(
    self,
    rel_id: str,
    source_id: str,
    target_id: str,
    rel_type: str,
    document_id: str,
    properties: Dict[str, Any],
    confidence_score: float
) -> bool:
    """
    Create relationship between entities.
    
    Args:
        rel_id: Unique relationship identifier
        source_id: Source entity ID
        target_id: Target entity ID
        rel_type: Relationship type (automatically converted to ALL CAPS)
        document_id: Source document ID
        properties: Additional relationship properties
        confidence_score: Extraction confidence
        
    Returns:
        bool: Creation success status
        
    Features:
        - Automatic ALL CAPS conversion (works_for → WORKS_FOR)
        - Type standardization and validation
        - Duplicate relationship prevention
        - Property normalization
    """
```

##### `_sanitize_label(label: str) -> str`

**Converts entity types to valid Neo4j labels.**

```python
def _sanitize_label(self, label: str) -> str:
    """
    Convert entity type to valid Neo4j label.
    
    Args:
        label: Raw entity type string
        
    Returns:
        str: Sanitized Neo4j label
        
    Rules:
        - Convert to uppercase
        - Replace spaces/hyphens with underscores
        - Remove invalid characters
        - Ensure starts with letter/underscore
        - Handle empty/invalid inputs
        
    Examples:
        'PERSON' → 'PERSON'
        'API Service' → 'API_SERVICE'
        '2-factor-auth' → 'TYPE_2_FACTOR_AUTH'
        '' → 'UNKNOWN'
    """
```

---

### SupabaseManager

**Location**: `src/akg/database/supabase_manager.py`

Manages Supabase operations for document storage and domain type caching.

#### Constructor

```python
def __init__(self, url: str, key: str):
    """
    Initialize Supabase manager.
    
    Args:
        url: Supabase project URL
        key: Supabase API key (anon or service role)
    """
```

#### Core Methods

##### `store_document(document: Document) -> bool`

**Stores document metadata in Supabase.**

```python
async def store_document(self, document: Document) -> bool:
    """
    Store document in Supabase documents table.
    
    Args:
        document: Document object to store
        
    Returns:
        bool: Storage success status
        
    Features:
        - Content hash generation for deduplication
        - Metadata normalization
        - Processing status tracking
        - Error handling and logging
    """
```

##### `get_domain_entity_types(domain: str, limit: int = 50) -> List[Dict]`

**Retrieves domain-specific entity types for fallback.**

```python
async def get_domain_entity_types(
    self, 
    domain: str, 
    limit: int = 50
) -> List[Dict]:
    """
    Get entity types for a specific domain.
    
    Args:
        domain: Domain name (technical, business, legal)
        limit: Maximum types to return
        
    Returns:
        List of entity type dictionaries with:
        - entity_type: Type name
        - usage_count: Frequency of use
        - confidence_score: Type confidence
        - description: Type description
        
    Use Cases:
        - AI service fallback
        - Type suggestion for new domains
        - Domain analysis and statistics
    """
```

##### `store_domain_entity_type(domain, entity_type, confidence_score, source) -> bool`

**Stores discovered entity types by domain.**

```python
async def store_domain_entity_type(
    self,
    domain: str,
    entity_type: str,
    confidence_score: float,
    source: str = "document_analysis"
) -> bool:
    """
    Store or update domain-specific entity type.
    
    Args:
        domain: Primary domain classification
        entity_type: Entity type name
        confidence_score: Type confidence (0.0-1.0)
        source: Discovery method (document_analysis, manual, ai_generated)
        
    Returns:
        bool: Storage success status
        
    Features:
        - Automatic usage count increment
        - Confidence score averaging
        - Duplicate handling with updates
        - Domain-specific organization
    """
```

---

### TypeManager

**Location**: `src/akg/agents/type_manager.py`

Manages dynamic type discovery and caching across the system.

#### Constructor

```python
def __init__(self, neo4j_manager=None):
    """
    Initialize type manager with Neo4j connection.
    
    Args:
        neo4j_manager: Neo4jManager instance for type queries
    """
```

#### Core Methods

##### `refresh_type_cache() -> None`

**Updates type cache from Neo4j database.**

```python
async def refresh_type_cache(self) -> None:
    """
    Refresh entity and relationship type caches from Neo4j.
    
    Process:
        1. Query all distinct entity types from Neo4j
        2. Query all distinct relationship types
        3. Update internal cache dictionaries
        4. Log cache statistics
        
    Cache Contents:
        - _entity_types_cache: Set of all entity types
        - _relationship_types_cache: Set of all relationship types
        
    Called:
        - Before each extraction to get latest types
        - After saving new entities/relationships
        - On system initialization
    """
```

##### `resolve_entity_type(candidate_type: str) -> str`

**Normalizes and resolves entity types with fuzzy matching.**

```python
def resolve_entity_type(self, candidate_type: str) -> str:
    """
    Resolve entity type with fuzzy matching and normalization.
    
    Args:
        candidate_type: Raw entity type from extraction
        
    Returns:
        str: Normalized entity type
        
    Process:
        1. Normalize case and formatting
        2. Check exact matches in cache
        3. Apply fuzzy matching for similar types
        4. Use similarity threshold (0.8) for matching
        5. Return best match or original if no good match
        
    Examples:
        'person' → 'PERSON' (if PERSON exists in cache)
        'api service' → 'API_SERVICE' (fuzzy match)
        'novel_type' → 'NOVEL_TYPE' (new type, kept as-is)
    """
```

---

### Document Processing Models

**Location**: `src/akg/models.py`

Core Pydantic models for data validation and serialization.

#### Document

```python
class Document(BaseModel):
    """
    Represents a source document being processed.
    
    Attributes:
        id: Unique document identifier
        title: Document title/name
        content: Full document text content
        source_system: Origin system (default: "local_files")
        source_path: File path or URL
        document_type: Classification (pdf, docx, meeting_notes)
        metadata: Additional document properties
        processed_at: Processing timestamp
        created_at: Creation timestamp
    """
```

#### Entity

```python
class Entity(BaseModel):
    """
    Represents an extracted entity.
    
    Attributes:
        id: Unique entity identifier
        name: Entity name/title
        entity_type: Type classification (PERSON, API, etc.)
        document_id: Source document reference
        properties: Additional entity attributes
        aliases: Alternative names for the entity
        confidence_score: Extraction confidence (0.0-1.0)
        created_at: Creation timestamp
    """
```

#### Relationship

```python
class Relationship(BaseModel):
    """
    Represents a relationship between entities.
    
    Attributes:
        id: Unique relationship identifier
        source_entity_id: Source entity reference
        target_entity_id: Target entity reference
        relationship_type: Type (WORKS_FOR, MANAGES, etc.)
        document_id: Source document reference
        properties: Additional relationship attributes
        confidence_score: Extraction confidence (0.0-1.0)
        created_at: Creation timestamp
    """
```

---

### Configuration Management

**Location**: `src/akg/config.py`

Pydantic-based configuration with environment variable support.

#### AKGConfig

```python
class AKGConfig(BaseSettings):
    """
    Application configuration with environment variable support.
    
    Configuration Categories:
        - Google Gemini: AI service configuration
        - LlamaParse: Document parsing service
        - Neo4j: Graph database settings
        - Supabase: Document storage and caching
        - Application: Processing parameters
        - Graph: Graph-specific settings
        - Local Files: File ingestion configuration
    """
```

#### Key Configuration Options

```python
# AI Services
google_api_key: str              # Required: Google Gemini API key
llama_cloud_api_key: str         # Required: LlamaParse API key

# Databases
neo4j_uri: str = "bolt://localhost:7687"
neo4j_username: str = "neo4j"
neo4j_password: str              # Required
supabase_url: str                # Required
supabase_api_key: str            # Required

# Processing
chunk_size: int = 1000           # Document chunk size
overlap_size: int = 200          # Chunk overlap
max_concurrent_documents: int = 5 # Parallel processing limit

# Graph
similarity_threshold: float = 0.8 # Entity matching threshold
provenance_enabled: bool = True   # Track data lineage

# File Processing
documents_input_dir: str = "./documents"
supported_file_types: str = "pdf,docx,txt,md,html,pptx,xlsx"
watch_directory: bool = True      # Monitor for file changes
```

## Error Handling Patterns

### Standard Error Handling

All async methods follow this pattern:

```python
try:
    # Main operation
    result = await operation()
    logger.info(f"✅ Operation successful: {result}")
    return result
except SpecificException as e:
    logger.error(f"❌ Specific error: {e}")
    # Handle specific case
    return fallback_value
except Exception as e:
    logger.error(f"❌ Unexpected error: {e}")
    # Log full traceback in debug mode
    raise
```

### Database Connection Patterns

```python
async def database_operation(self):
    """Standard database operation pattern."""
    if not self.driver:
        await self.initialize()
    
    async with self.driver.session() as session:
        try:
            result = await session.run(query, parameters)
            return result.data()
        except neo4j.exceptions.ServiceUnavailable:
            logger.error("Database unavailable")
            return None
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise
```

## Performance Considerations

### Query Optimization

- **Use dynamic labels**: `MATCH (n:PERSON)` instead of `MATCH (n:Entity) WHERE n.type = "PERSON"`
- **Limit result sets**: Always use `LIMIT` in development queries
- **Index on frequently queried properties**: Create indexes for name, type, document_id
- **Batch operations**: Group multiple creates/updates in single transactions

### Memory Management

- **Stream large results**: Use pagination for large entity sets
- **Limit concurrent processing**: Configure `max_concurrent_documents`
- **Clear caches periodically**: Type manager caches grow over time

### Caching Strategy

- **Document analysis cache**: Avoids re-analyzing similar documents
- **Type caches**: Reduces database queries for type resolution
- **Connection pooling**: Neo4j driver handles connection reuse

This API reference provides detailed documentation for all core classes and methods in the AKG system.
