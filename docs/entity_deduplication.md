# Entity Deduplication System

## Overview

The AKG system now includes a comprehensive entity and relationship deduplication system to prevent the creation of duplicate nodes in the knowledge graph. This system ensures that similar entities are identified and reused instead of creating new duplicate nodes.

## Features

### 1. Enhanced Entity Deduplication

The system now performs multi-level entity matching:

#### **Level 1: Exact Match**
- Looks for entities with exactly the same name and type
- Highest priority - immediate reuse if found
- Example: "John Smith" (PERSON) matches exactly with existing "John Smith" (PERSON)

#### **Level 2: Fuzzy Matching within Type**
- Uses advanced similarity algorithms with multiple strategies:
  - **Exact Match**: Normalized case-insensitive matching
  - **Contains Match**: Partial string matching (bidirectional)
  - **Word Match**: Matches entities sharing significant words
- Configurable similarity threshold (default: 0.8)
- Only matches entities of the same type
- Example: "John Smith" matches with "John W. Smith" (same type)

#### **Level 3: Cross-Type Matching**
- Searches across all entity types for very high similarity matches
- Higher threshold required (default: 0.95)
- Useful for cases where entity type classification might vary
- Example: "Apple Inc." (COMPANY) might match "Apple" (ORGANIZATION)

### 2. Relationship Deduplication

- Checks for existing relationships between the same entities
- Prevents duplicate relationships of the same type
- Configurable via `enable_relationship_deduplication` setting

### 3. Configuration Options

Add these environment variables to control deduplication behavior:

```bash
# Enable/disable entity deduplication (default: true)
ENABLE_ENTITY_DEDUPLICATION=true

# Similarity threshold for same-type matching (default: 0.8)
ENTITY_SIMILARITY_THRESHOLD=0.8

# Similarity threshold for cross-type matching (default: 0.95)
CROSS_TYPE_SIMILARITY_THRESHOLD=0.95

# Enable/disable relationship deduplication (default: true)
ENABLE_RELATIONSHIP_DEDUPLICATION=true
```

## How It Works

### Entity Processing Flow

1. **Extract Entity**: AI extracts entity from document
2. **Type Resolution**: TypeManager resolves entity type
3. **Deduplication Check**:
   - Search for exact matches
   - Search for similar entities within type
   - Search for cross-type matches (if enabled)
4. **Decision**:
   - If good match found: Reuse existing entity ID
   - If no match found: Create new entity
5. **Logging**: Clear indication of reuse vs. creation

### Relationship Processing Flow

1. **Extract Relationship**: AI extracts relationship from document
2. **Entity Resolution**: Resolve source and target entity IDs
3. **Duplicate Check**: Search for existing relationship between same entities
4. **Decision**:
   - If relationship exists: Skip creation
   - If new relationship: Create new relationship

## Benefits

### 1. Reduced Data Duplication
- Eliminates duplicate entities with similar names
- Prevents relationship duplication
- Creates cleaner, more connected knowledge graphs

### 2. Better Graph Connectivity
- Similar entities are merged, increasing node connectivity
- Relationships point to the same canonical entities
- Improved graph traversal and analysis

### 3. Improved Data Quality
- Consistent entity representation
- Reduced ambiguity in entity references
- Better support for entity linking and resolution

### 4. Performance Improvements
- Fewer nodes to store and query
- More efficient graph operations
- Reduced storage requirements

## Monitoring and Logs

The system provides detailed logging for deduplication activities:

```
🔍 Looking for existing entity: 'John Smith' (type: PERSON)
📌 Found exact match for 'John Smith': reusing entity abc-123-def
🎯 High confidence match for 'Apple' -> 'Apple Inc.' (score: 0.92, type: exact_match): reusing entity xyz-456-abc
✨ Creating new entity: 'Microsoft' (type: COMPANY) with ID new-789-ghi
📌 Relationship already exists: John Smith -> Apple Inc. (WORKS_FOR)
🔗 New relationship type: John Smith -> Microsoft (FOUNDED)
```

## Performance Considerations

### 1. Timeout Handling
- Each deduplication query has a 5-second timeout
- System continues gracefully if queries timeout
- Fallback to creating new entities if lookup fails

### 2. Caching
- TypeManager caches entity and relationship types
- Reduces repeated queries to Neo4j
- Periodic cache refresh for consistency

### 3. Configurable Thresholds
- Adjust similarity thresholds based on data quality needs
- Higher thresholds = fewer matches, more precision
- Lower thresholds = more matches, potential false positives

## Best Practices

### 1. Threshold Tuning
- Start with default thresholds (0.8 for same-type, 0.95 for cross-type)
- Monitor logs to see matching behavior
- Adjust based on your data characteristics

### 2. Type Consistency
- Ensure consistent entity type classification
- Use TypeManager's type resolution features
- Review and clean up entity types periodically

### 3. Monitoring
- Regularly check deduplication logs
- Monitor graph growth rates
- Validate that similar entities are being properly merged

## Troubleshooting

### Common Issues

1. **Too Many Duplicates**: Lower similarity thresholds
2. **False Merges**: Raise similarity thresholds
3. **Performance Issues**: Check Neo4j indexing and query performance
4. **Timeout Errors**: Review Neo4j connection and server performance

### Debugging

Enable debug logging to see detailed matching information:
```bash
LOG_LEVEL=DEBUG
```

This will show all similarity matching attempts and scores.
