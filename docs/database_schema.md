# Database Schema Documentation

## Overview

The AKG system uses a dual-database architecture:
- **Neo4j**: Graph database for entities and relationships
- **Supabase**: PostgreSQL for document storage and domain type caching

## Neo4j Schema

### Node Types

#### Entity Nodes

**Labels**: `:Entity` (base) + `:SPECIFIC_TYPE` (dynamic)

```cypher
// Example entity nodes
CREATE (p:Entity:PERSON {
    id: "entity-uuid",
    name: "John Doe",
    type: "PERSON",
    document_id: "doc-uuid",
    confidence_score: 0.95,
    created_at: datetime(),
    properties: {role: "Developer", team: "Backend"}
})

CREATE (a:Entity:API {
    id: "entity-uuid",
    name: "User Management API",
    type: "API",
    document_id: "doc-uuid",
    confidence_score: 0.90,
    created_at: datetime(),
    properties: {version: "v2.1", status: "production"}
})
```

**Standard Properties**:
- `id`: Unique identifier (string)
- `name`: Entity name/title (string)
- `type`: Entity classification (string, matches dynamic label)
- `document_id`: Source document reference (string)
- `confidence_score`: Extraction confidence 0.0-1.0 (float)
- `created_at`: Creation timestamp (datetime)
- `properties`: Additional attributes (JSON/map)

**Dynamic Labels**:
- `:PERSON` - Human individuals
- `:API` - Application programming interfaces
- `:SERVICE` - Software services/microservices
- `:DATABASE` - Data storage systems
- `:FUNCTION` - Software functions/methods
- `:CLASS` - Object-oriented classes
- `:TEAM` - Groups of people
- `:PROJECT` - Business projects/initiatives
- `:BUDGET` - Financial allocations
- `:CONTRACT` - Legal agreements
- `:DOCUMENT` - Document references
- `:ALGORITHM` - Algorithms/procedures

#### Document Nodes

```cypher
CREATE (d:Document {
    id: "doc-uuid",
    title: "API Specification",
    source_path: "/documents/api_spec.md",
    document_type: "technical_specification",
    processed_at: datetime(),
    created_at: datetime(),
    metadata: {domain: "technical", size: 15000}
})
```

### Relationship Types

All relationship types follow ALL CAPS naming convention.

#### Business Domain
- `WORKS_FOR` - Employment relationship
- `MANAGES` - Management hierarchy
- `REPORTS_TO` - Reporting structure
- `ASSIGNED_TO` - Task/project assignment
- `OWNS` - Ownership relationship
- `HAS_BUDGET` - Budget allocation
- `FUNDED_BY` - Funding source

#### Technical Domain
- `INTEGRATES_WITH` - System integration
- `DEPENDS_ON` - Dependency relationship
- `CALLS` - Function/API calls
- `RETURNS` - Function return values
- `IMPLEMENTS` - Interface implementation
- `EXTENDS` - Class inheritance
- `USES` - Technology/tool usage
- `DEPLOYED_ON` - Deployment relationship

#### Legal Domain
- `GOVERNED_BY` - Legal governance
- `BOUND_BY` - Legal obligations
- `REFERS_TO` - Document references
- `SUPERSEDES` - Document versioning
- `INCLUDES_CLAUSE` - Contract provisions

#### Temporal Relationships
- `OCCURRED_ON` - Event timing
- `SCHEDULED_FOR` - Future events
- `DEADLINE_IS` - Time constraints
- `STARTED_ON` - Beginning dates
- `COMPLETED_ON` - End dates

### Indexes and Constraints

```cypher
-- Entity indexes for performance
CREATE INDEX entity_id_index IF NOT EXISTS FOR (e:Entity) ON (e.id);
CREATE INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type);
CREATE INDEX entity_document_index IF NOT EXISTS FOR (e:Entity) ON (e.document_id);

-- Document indexes
CREATE INDEX document_id_index IF NOT EXISTS FOR (d:Document) ON (d.id);
CREATE INDEX document_title_index IF NOT EXISTS FOR (d:Document) ON (d.title);

-- Uniqueness constraints
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;

-- Type-specific indexes for dynamic labels
CREATE INDEX person_name_index IF NOT EXISTS FOR (p:PERSON) ON (p.name);
CREATE INDEX api_name_index IF NOT EXISTS FOR (a:API) ON (a.name);
CREATE INDEX service_name_index IF NOT EXISTS FOR (s:SERVICE) ON (s.name);
```

### Query Patterns

#### Basic Entity Queries

```cypher
-- Find all persons
MATCH (p:PERSON) RETURN p;

-- Find entities by type (works with old and new style)
MATCH (e:Entity) WHERE e.type = "PERSON" RETURN e;

-- Find entities from specific document
MATCH (e:Entity) WHERE e.document_id = "doc-uuid" RETURN e;
```

#### Relationship Queries

```cypher
-- Find who manages whom
MATCH (manager:PERSON)-[:MANAGES]->(employee:PERSON) 
RETURN manager.name, employee.name;

-- Find API dependencies
MATCH (api:API)-[:DEPENDS_ON]->(service:SERVICE)
RETURN api.name, service.name;

-- Find project team members
MATCH (person:PERSON)-[:ASSIGNED_TO]->(project:PROJECT)
RETURN project.name, collect(person.name) as team_members;
```

#### Performance Queries

```cypher
-- Check label distribution
CALL db.labels() YIELD label
MATCH (n) WHERE label IN labels(n)
RETURN label, count(n) as usage_count
ORDER BY usage_count DESC;

-- Find non-compliant relationship types (should be ALL CAPS)
MATCH ()-[r]->()
WHERE type(r) =~ '.*[a-z].*'
RETURN DISTINCT type(r) as non_caps_relationships;

-- Entity type statistics
MATCH (e:Entity)
RETURN e.type, count(e) as count, labels(e) as labels
ORDER BY count DESC;
```

---

## Supabase Schema

### Core Tables

#### documents

Primary table for document metadata and content.

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT,
    content_hash TEXT, -- MD5 hash for deduplication
    source_system TEXT DEFAULT 'local_files',
    source_path TEXT NOT NULL,
    document_type TEXT,
    metadata JSONB DEFAULT '{}',
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(source_path, source_system)
);
```

**Indexes**:
```sql
CREATE INDEX idx_documents_title ON documents(title);
CREATE INDEX idx_documents_content_hash ON documents(content_hash);
CREATE INDEX idx_documents_source_path ON documents(source_path);
CREATE INDEX idx_documents_document_type ON documents(document_type);
CREATE INDEX idx_documents_processed_at ON documents(processed_at);
```

#### domain_entity_types

Stores entity types organized by domain for intelligent fallbacks.

```sql
CREATE TABLE domain_entity_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    subdomain TEXT,
    entity_type TEXT NOT NULL,
    description TEXT,
    usage_count INTEGER DEFAULT 0,
    confidence_score FLOAT DEFAULT 0.0,
    source TEXT NOT NULL DEFAULT 'document_analysis',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(domain, subdomain, entity_type)
);
```

**Sources**:
- `document_analysis` - Discovered during AI processing
- `manual` - Manually curated types
- `ai_generated` - Generated by AI models
- `pattern_based` - Discovered by pattern matching

**Indexes**:
```sql
CREATE INDEX idx_domain_entity_types_domain ON domain_entity_types(domain);
CREATE INDEX idx_domain_entity_types_subdomain ON domain_entity_types(subdomain);
CREATE INDEX idx_domain_entity_types_usage_count ON domain_entity_types(usage_count DESC);
CREATE INDEX idx_domain_entity_types_confidence ON domain_entity_types(confidence_score DESC);
```

#### domain_relationship_types

Stores relationship types with their source verbs for learning.

```sql
CREATE TABLE domain_relationship_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    subdomain TEXT,
    relationship_type TEXT NOT NULL,
    description TEXT,
    source_verb TEXT, -- Original verb from document
    usage_count INTEGER DEFAULT 0,
    confidence_score FLOAT DEFAULT 0.0,
    source TEXT NOT NULL DEFAULT 'document_analysis',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(domain, subdomain, relationship_type)
);
```

**Indexes**:
```sql
CREATE INDEX idx_domain_relationship_types_domain ON domain_relationship_types(domain);
CREATE INDEX idx_domain_relationship_types_subdomain ON domain_relationship_types(subdomain);
CREATE INDEX idx_domain_relationship_types_usage_count ON domain_relationship_types(usage_count DESC);
CREATE INDEX idx_domain_relationship_types_confidence ON domain_relationship_types(confidence_score DESC);
CREATE INDEX idx_domain_relationship_types_source_verb ON domain_relationship_types(source_verb);
```

#### domain_analysis_cache

Caches document analysis results to avoid re-processing similar documents.

```sql
CREATE TABLE domain_analysis_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_type TEXT,
    content_hash TEXT UNIQUE NOT NULL, -- MD5 of title + content preview
    domain TEXT NOT NULL,
    subdomain TEXT,
    description TEXT,
    key_entity_types JSONB DEFAULT '[]',
    key_relationship_types JSONB DEFAULT '[]',
    structural_elements JSONB DEFAULT '[]',
    content_focus TEXT,
    confidence FLOAT DEFAULT 0.0,
    analysis_method TEXT DEFAULT 'ai_generated',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Indexes**:
```sql
CREATE INDEX idx_domain_analysis_cache_domain ON domain_analysis_cache(domain);
CREATE INDEX idx_domain_analysis_cache_document_type ON domain_analysis_cache(document_type);
CREATE INDEX idx_domain_analysis_cache_content_hash ON domain_analysis_cache(content_hash);
```

#### verb_extractions

Tracks individual verb extractions for relationship learning.

```sql
CREATE TABLE verb_extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    original_verb TEXT NOT NULL,
    normalized_relationship TEXT NOT NULL,
    context_snippet TEXT, -- Surrounding text
    domain TEXT,
    confidence_score FLOAT DEFAULT 0.0,
    extraction_method TEXT DEFAULT 'regex',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Indexes**:
```sql
CREATE INDEX idx_verb_extractions_document_id ON verb_extractions(document_id);
CREATE INDEX idx_verb_extractions_domain ON verb_extractions(domain);
CREATE INDEX idx_verb_extractions_original_verb ON verb_extractions(original_verb);
CREATE INDEX idx_verb_extractions_normalized_relationship ON verb_extractions(normalized_relationship);
```

### Views and Analytics

#### domain_type_statistics

Aggregated statistics for domain type analysis.

```sql
CREATE VIEW domain_type_statistics AS
SELECT 
    domain,
    subdomain,
    COUNT(DISTINCT entity_type) as entity_types_count,
    (SELECT COUNT(DISTINCT relationship_type) 
     FROM domain_relationship_types drt 
     WHERE drt.domain = det.domain 
     AND (drt.subdomain = det.subdomain OR (drt.subdomain IS NULL AND det.subdomain IS NULL))
    ) as relationship_types_count,
    SUM(usage_count) as total_entity_usage,
    AVG(confidence_score) as avg_entity_confidence
FROM domain_entity_types det
GROUP BY domain, subdomain
ORDER BY total_entity_usage DESC;
```

#### top_domain_verbs

Most frequently used verbs by domain.

```sql
CREATE VIEW top_domain_verbs AS
SELECT 
    domain,
    subdomain,
    relationship_type,
    source_verb,
    usage_count,
    confidence_score,
    description
FROM domain_relationship_types
ORDER BY usage_count DESC, confidence_score DESC
LIMIT 100;
```

### Row Level Security (RLS)

```sql
-- Enable RLS on all tables
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain_entity_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain_relationship_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain_analysis_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE verb_extractions ENABLE ROW LEVEL SECURITY;

-- Development policies (allow all access)
CREATE POLICY "Enable all access for documents" ON documents FOR ALL USING (true);
CREATE POLICY "Enable all access for domain entity types" ON domain_entity_types FOR ALL USING (true);
CREATE POLICY "Enable all access for domain relationship types" ON domain_relationship_types FOR ALL USING (true);
CREATE POLICY "Enable all access for domain analysis cache" ON domain_analysis_cache FOR ALL USING (true);
CREATE POLICY "Enable all access for verb extractions" ON verb_extractions FOR ALL USING (true);
```

### Triggers

#### Updated At Triggers

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_documents_updated_at 
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_domain_entity_types_updated_at 
    BEFORE UPDATE ON domain_entity_types
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_domain_relationship_types_updated_at 
    BEFORE UPDATE ON domain_relationship_types
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_domain_analysis_cache_updated_at 
    BEFORE UPDATE ON domain_analysis_cache
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## Data Migration Patterns

### From Single Database to Dual Database

If migrating from a single-database approach:

```sql
-- Export entities from old system
COPY (
    SELECT id, name, type, properties, document_id, confidence_score, created_at
    FROM old_entities
) TO '/tmp/entities.csv' WITH CSV HEADER;

-- Import to Neo4j via application layer
-- (Use EntityExtractionAgent.save_to_neo4j method)

-- Migrate documents to Supabase
INSERT INTO documents (id, title, content, source_path, document_type, created_at)
SELECT id, title, content, source_path, document_type, created_at
FROM old_documents;
```

### Backup and Restore

#### Neo4j Backup
```bash
# Backup Neo4j database
neo4j-admin dump --database=neo4j --to=/backup/akg-graph.dump

# Restore Neo4j database
neo4j-admin load --from=/backup/akg-graph.dump --database=neo4j --force
```

#### Supabase Backup
```bash
# Backup Supabase (PostgreSQL)
pg_dump $SUPABASE_DB_URL > /backup/akg-supabase.sql

# Restore to new Supabase instance
psql $NEW_SUPABASE_DB_URL < /backup/akg-supabase.sql
```

## Performance Optimization

### Neo4j Optimizations

1. **Use Dynamic Labels**: Query `:PERSON` instead of filtering by type property
2. **Create Indexes**: On frequently queried properties
3. **Limit Results**: Always use `LIMIT` in development
4. **Batch Operations**: Group multiple operations in transactions

### Supabase Optimizations

1. **Index Strategy**: Create indexes on frequently queried columns
2. **Partitioning**: Consider partitioning large tables by date
3. **Connection Pooling**: Use PgBouncer for connection management
4. **Read Replicas**: Use read replicas for analytics queries

This schema documentation provides complete details for both Neo4j and Supabase database structures used in the AKG system.
