# Domain-Specific Fallback Types with Supabase

This document explains the new Supabase integration for storing and managing domain-specific entity and relationship types as fallback patterns.

## Overview

The system now uses Supabase to:
1. **Cache document analysis results** to avoid re-analyzing similar documents
2. **Store domain-specific entity types** learned from document analysis
3. **Store domain-specific relationship types** extracted from verbs in documents
4. **Track verb extractions** for improving relationship detection
5. **Provide fallback types** when AI services are unavailable

## Database Schema

### New Tables

#### `domain_entity_types`
Stores entity types organized by domain and subdomain:
```sql
- domain: Primary domain (technical, business, legal, etc.)
- subdomain: More specific classification
- entity_type: The actual entity type name
- usage_count: How many times this type has been used
- confidence_score: Confidence in this type (0.0-1.0)
- source: How the type was discovered (document_analysis, manual, ai_generated)
```

#### `domain_relationship_types`
Stores relationship types with their source verbs:
```sql
- domain: Primary domain
- relationship_type: The normalized relationship name
- source_verb: Original verb from document (e.g., "manages" → "MANAGES")
- usage_count: Usage frequency
- confidence_score: Confidence level
- source: Discovery method (verb_extraction, document_analysis)
```

#### `domain_analysis_cache`
Caches document analysis results:
```sql
- content_hash: MD5 hash of document title + content preview
- domain, subdomain: Analyzed domain classification
- key_entity_types, key_relationship_types: JSON arrays of suggested types
```

#### `verb_extractions`
Tracks individual verb extractions for analysis:
```sql
- document_id: Source document
- original_verb: Raw verb from text
- normalized_relationship: Converted relationship type
- context_snippet: Surrounding text
- extraction_method: How it was extracted (regex, ai_analysis)
```

## How It Works

### 1. Document Analysis with Caching

```python
# When analyzing a document:
content_hash = hashlib.md5(f"{title}:{content[:2000]}".encode()).hexdigest()

# Check cache first
cached_analysis = await supabase_manager.get_domain_analysis_cache(content_hash)
if cached_analysis:
    return cached_analysis

# Perform fresh analysis and cache results
analysis_data = perform_analysis(document)
await supabase_manager.store_domain_analysis_cache(content_hash, analysis_data)
```

### 2. Domain Type Storage

When extracting entities and relationships, the system automatically stores discovered types:

```python
# Store entity types by domain
await supabase_manager.store_domain_entity_type(
    domain="technical",
    entity_type="API",
    confidence_score=0.9,
    source="document_analysis"
)

# Store relationship types with source verbs
await supabase_manager.store_domain_relationship_type(
    domain="technical", 
    relationship_type="INTEGRATES_WITH",
    source_verb="integrates",
    confidence_score=0.8,
    source="verb_extraction"
)
```

### 3. Verb Extraction and Storage

The system extracts verbs from document text and stores them for learning:

```python
# Extract verbs between entities
verb_patterns = [
    r'entity1\s+(\w+)\s+.*?entity2',
    r'(\w+)\s+entity1\s+.*?entity2'
]

# Store each extraction
await supabase_manager.store_verb_extraction(
    document_id=doc.id,
    original_verb="manages",
    normalized_relationship="MANAGES", 
    context_snippet=surrounding_text,
    domain="business"
)
```

### 4. Fallback Type Retrieval

When AI services are unavailable, the system retrieves stored domain types:

```python
# Get domain-specific types for fallback
technical_entities = await supabase_manager.get_domain_entity_types(
    domain="technical",
    limit=50
)

technical_relationships = await supabase_manager.get_domain_relationship_types(
    domain="technical", 
    limit=50
)
```

## Usage

### Setup Supabase

1. **Run the schema migration**:
   ```sql
   -- In your Supabase SQL editor
   \i database/domain_types_schema.sql
   ```

2. **Set environment variables**:
   ```bash
   export SUPABASE_URL="your-supabase-url"
   export SUPABASE_ANON_KEY="your-anon-key"
   ```

### Initialize with Supabase Support

```python
from src.akg.agents.extraction import EntityExtractionAgent
from src.akg.database.supabase_manager import SupabaseManager

# Initialize Supabase manager
supabase_manager = SupabaseManager(supabase_url, supabase_key)
await supabase_manager.initialize()

# Create extraction agent with Supabase support
extractor = EntityExtractionAgent(
    neo4j_manager=neo4j_manager,
    supabase_manager=supabase_manager
)
```

### Extract with Domain Learning

```python
# Extract entities and relationships
# This automatically stores discovered domain types in Supabase
entities, relationships = await extractor.extract_entities_and_relationships(document)
```

### Query Domain Statistics

```python
# Get domain type statistics
stats = await supabase_manager.get_domain_statistics()

print(f"Total Entity Types: {stats['total_entity_types']}")
print(f"Total Relationship Types: {stats['total_relationship_types']}")

# Get types for specific domain
tech_entities = await supabase_manager.get_domain_entity_types("technical")
tech_relationships = await supabase_manager.get_domain_relationship_types("technical")
```

## Benefits

### 1. **Improved Performance**
- Document analysis results are cached
- Avoid re-analyzing similar documents
- Faster fallback extraction with pre-learned types

### 2. **Better Domain Adaptation**
- System learns from each document processed
- Domain-specific types improve over time
- More accurate extraction for specialized domains

### 3. **Robust Fallback**
- Rich fallback types when AI services unavailable
- Types are learned from actual document content
- Verb-based relationships from real usage

### 4. **Analytics and Insights**
- Track which domains are most common
- See which verbs generate which relationships
- Monitor system learning and adaptation

### 5. **Scalable Learning**
- New domains are automatically detected
- Types accumulate usage statistics
- Confidence scores improve with usage

## Testing

Run the test script to verify Supabase integration:

```bash
# Set environment variables first
export SUPABASE_URL="your-url"
export SUPABASE_ANON_KEY="your-key"

# Run the test
python test_supabase_domain_types.py
```

The test will:
- Initialize Supabase connection
- Process a test document with domain-specific content
- Store entity types, relationship types, and verb extractions
- Retrieve and display stored domain types
- Show domain statistics
- Test fallback behavior without Supabase

## Migration from Previous Version

The system maintains backward compatibility:
- Extraction works without Supabase (falls back to in-memory patterns)
- Neo4j integration remains unchanged
- Existing extraction logic is preserved

To enable Supabase features:
1. Run the schema migration
2. Set environment variables
3. Pass `supabase_manager` to `EntityExtractionAgent`

## Future Enhancements

1. **Cross-document Type Correlation**: Analyze how types relate across different documents
2. **Domain Confidence Scoring**: Improve confidence calculations based on usage patterns
3. **Type Recommendation**: Suggest entity/relationship types for new domains
4. **Manual Type Curation**: Interface for reviewing and approving discovered types
5. **Export/Import**: Backup and restore domain type collections
