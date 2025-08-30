# Copilot Instructions for AKG (Automated Knowledge Graph)

## Architecture Overview
This is a document-to-knowledge-graph system with a **dual-database architecture**:
- **Supabase**: Document storage, metadata, and provenance tracking
- **Neo4j**: Graph database for entities, relationships, and knowledge graph queries

### Core Workflow
1. **Ingestion** (`src/akg/agents/ingestion.py`) → Hash-based change detection → Supabase storage
2. **Extraction** (`src/akg/agents/extraction.py`) → **Document chunking** (2000 chars, 200 overlap) → **Gemini AI** → SPO triples
3. **Graph Construction** → **ALL CAPS relationship types** → Neo4j storage with full provenance

## Key Patterns & Conventions

### Document Chunking Strategy
```python
# ALL extraction uses smart chunking - never process full documents directly
chunks = self._chunk_document(document.content, chunk_size=2000, overlap=200)
for chunk in chunks:
    entities, relationships = await self._extract_from_chunk(chunk)
```

### ALL CAPS Relationship Types
```python
# CRITICAL: All relationship types MUST be uppercase
relationship_type = raw_type.upper()  # WORKS_FOR, MANAGES, HAS_BUDGET
```

### Type Resolution Pattern
```python
# Always use TypeManager for entity/relationship type consistency
resolved_type, is_new = await self.type_manager.resolve_entity_type(raw_type)
# Handles deduplication: "organisation" → "organization", "CEO" → "person"
```

## Database Interactions

### Supabase Patterns
```python
# Document storage with metadata tracking
await self.supabase_manager.store_document(document)
existing = self.supabase_manager.get_document_by_path(file_path)
```

### Neo4j Patterns
```python
# Dynamic relationship creation (NOT static RELATES_TO)
MERGE (s)-[r:`{relationship_type.upper()}`]->(t)
# Graph statistics for monitoring
stats = await neo4j_manager.get_graph_statistics()
```

## Testing Architecture

### Async Test Pattern
```python
@pytest.mark.asyncio
async def test_function(self, fixture_agent, sample_document):
    # Always use AsyncMock for database operations
    fixture_agent.neo4j_manager.create_entity = AsyncMock(return_value="entity-id")
```

### Mock Database Pattern
```python
# conftest.py provides comprehensive mocks
mock_neo4j_manager.get_existing_entity_types.return_value = {"person", "organization"}
mock_supabase_manager.store_document.return_value = {"id": "doc-123"}
```

## Development Workflows

### Run System
```bash
python run.py  # Main entry point - processes all documents
```

### Testing
```bash
python -m pytest tests/ -v  # 71+ comprehensive tests
python tests/clear_and_reprocess.py  # Reset databases and reprocess
```

### Debug Entity Extraction
```python
# Enable detailed logging to trace Gemini AI responses
logger.info(f"🤖 Gemini response: {response_text}")
# Check fallback activation when AI fails
logger.warning("🔄 Falling back to pattern-based extraction")
```

## Critical Implementation Details

### SPO (Subject-Predicate-Object) Focused Prompts
```python
# Extraction prompts specifically request SPO triples format
prompt = f"""Extract SUBJECT-PREDICATE-OBJECT relationships from this text:
{chunk}

Focus on: {', '.join(existing_entity_types)} entities
Relationships: {', '.join(existing_relationship_types)}"""
```

### Error Handling Patterns
```python
# Graceful degradation: AI fails → pattern matching → continue processing
try:
    return await self._extract_with_gemini(chunk)
except Exception as e:
    logger.warning(f"Gemini extraction failed: {e}")
    return await self.fallback_extractor.extract_entities(chunk)
```

### Configuration Management
- Environment variables loaded via `AKGConfig` (Pydantic settings)
- Credentials: `GOOGLE_API_KEY`, `NEO4J_PASSWORD`, `SUPABASE_API_KEY`
- Chunking defaults: 2000 chars, 200 overlap (configurable)

## File Organization Logic
- `src/akg/models.py`: Pydantic data models (Document, Entity, Relationship)
- `src/akg/agents/`: Core processing agents (ingestion, extraction, type_manager)
- `src/akg/database/`: Database managers (neo4j_manager, supabase_manager)
- `tests/`: Comprehensive test suite with AsyncMock patterns and shared fixtures

## Integration Points
- **Google Gemini**: Entity/relationship extraction via `google.generativeai`
- **LlamaParse**: Document parsing for PDFs/complex formats
- **Rich Console**: Progress indicators and formatted output
- **Neo4j**: Graph operations via async driver patterns
- **Supabase**: Document storage via async client patterns
