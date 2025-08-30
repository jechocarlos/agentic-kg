-- Migration: create_domain_types_schema
-- Description: Create tables for domain-specific entity and relationship types
-- This migration should be applied via: supabase migration new create_domain_types_schema

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create domain_entity_types table for storing entity types by domain
CREATE TABLE IF NOT EXISTS domain_entity_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    subdomain TEXT,
    entity_type TEXT NOT NULL,
    description TEXT,
    usage_count INTEGER DEFAULT 0,
    confidence_score FLOAT DEFAULT 0.0,
    source TEXT NOT NULL DEFAULT 'document_analysis', -- document_analysis, manual, ai_generated, pattern_based
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure uniqueness per domain
    UNIQUE(domain, subdomain, entity_type)
);

-- Create domain_relationship_types table for storing relationship types by domain
CREATE TABLE IF NOT EXISTS domain_relationship_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    subdomain TEXT,
    relationship_type TEXT NOT NULL,
    description TEXT,
    source_verb TEXT, -- the original verb from the document
    usage_count INTEGER DEFAULT 0,
    confidence_score FLOAT DEFAULT 0.0,
    source TEXT NOT NULL DEFAULT 'document_analysis', -- document_analysis, manual, ai_generated, verb_extraction
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure uniqueness per domain
    UNIQUE(domain, subdomain, relationship_type)
);

-- Create domain_analysis_cache table for caching document analysis results
CREATE TABLE IF NOT EXISTS domain_analysis_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_type TEXT,
    content_hash TEXT, -- hash of document content for caching
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
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Index for fast lookup
    UNIQUE(content_hash)
);

-- Create verb_extractions table for tracking verb extraction patterns
CREATE TABLE IF NOT EXISTS verb_extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    original_verb TEXT NOT NULL,
    normalized_relationship TEXT NOT NULL,
    context_snippet TEXT, -- the surrounding text where the verb was found
    domain TEXT,
    confidence_score FLOAT DEFAULT 0.0,
    extraction_method TEXT DEFAULT 'regex', -- regex, ai_analysis, manual
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_domain_entity_types_domain ON domain_entity_types(domain);
CREATE INDEX IF NOT EXISTS idx_domain_entity_types_subdomain ON domain_entity_types(subdomain);
CREATE INDEX IF NOT EXISTS idx_domain_entity_types_usage_count ON domain_entity_types(usage_count DESC);
CREATE INDEX IF NOT EXISTS idx_domain_entity_types_confidence ON domain_entity_types(confidence_score DESC);

CREATE INDEX IF NOT EXISTS idx_domain_relationship_types_domain ON domain_relationship_types(domain);
CREATE INDEX IF NOT EXISTS idx_domain_relationship_types_subdomain ON domain_relationship_types(subdomain);
CREATE INDEX IF NOT EXISTS idx_domain_relationship_types_usage_count ON domain_relationship_types(usage_count DESC);
CREATE INDEX IF NOT EXISTS idx_domain_relationship_types_confidence ON domain_relationship_types(confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_domain_relationship_types_source_verb ON domain_relationship_types(source_verb);

CREATE INDEX IF NOT EXISTS idx_domain_analysis_cache_domain ON domain_analysis_cache(domain);
CREATE INDEX IF NOT EXISTS idx_domain_analysis_cache_document_type ON domain_analysis_cache(document_type);
CREATE INDEX IF NOT EXISTS idx_domain_analysis_cache_content_hash ON domain_analysis_cache(content_hash);

CREATE INDEX IF NOT EXISTS idx_verb_extractions_document_id ON verb_extractions(document_id);
CREATE INDEX IF NOT EXISTS idx_verb_extractions_domain ON verb_extractions(domain);
CREATE INDEX IF NOT EXISTS idx_verb_extractions_original_verb ON verb_extractions(original_verb);
CREATE INDEX IF NOT EXISTS idx_verb_extractions_normalized_relationship ON verb_extractions(normalized_relationship);

-- Add updated_at triggers for new tables
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_domain_entity_types_updated_at 
    BEFORE UPDATE ON domain_entity_types
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_domain_relationship_types_updated_at 
    BEFORE UPDATE ON domain_relationship_types
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_domain_analysis_cache_updated_at 
    BEFORE UPDATE ON domain_analysis_cache
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS for new tables
ALTER TABLE domain_entity_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain_relationship_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain_analysis_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE verb_extractions ENABLE ROW LEVEL SECURITY;

-- Create policies for development (allow all access)
CREATE POLICY "Enable all access for domain entity types" ON domain_entity_types FOR ALL USING (true);
CREATE POLICY "Enable all access for domain relationship types" ON domain_relationship_types FOR ALL USING (true);
CREATE POLICY "Enable all access for domain analysis cache" ON domain_analysis_cache FOR ALL USING (true);
CREATE POLICY "Enable all access for verb extractions" ON verb_extractions FOR ALL USING (true);

-- Create useful views for domain type analytics
CREATE VIEW domain_type_statistics AS
SELECT 
    domain,
    subdomain,
    COUNT(DISTINCT entity_type) as entity_types_count,
    (SELECT COUNT(DISTINCT relationship_type) 
     FROM domain_relationship_types drt 
     WHERE drt.domain = det.domain AND (drt.subdomain = det.subdomain OR (drt.subdomain IS NULL AND det.subdomain IS NULL))) as relationship_types_count,
    SUM(usage_count) as total_entity_usage,
    AVG(confidence_score) as avg_entity_confidence
FROM domain_entity_types det
GROUP BY domain, subdomain
ORDER BY total_entity_usage DESC;

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

-- Insert some initial domain types for common domains
INSERT INTO domain_entity_types (domain, entity_type, description, confidence_score, source) VALUES
    ('technical', 'API', 'Application Programming Interface', 0.9, 'manual'),
    ('technical', 'SERVICE', 'Software service or microservice', 0.9, 'manual'),
    ('technical', 'DATABASE', 'Data storage system', 0.9, 'manual'),
    ('technical', 'FUNCTION', 'Software function or method', 0.9, 'manual'),
    ('technical', 'CLASS', 'Object-oriented class', 0.9, 'manual'),
    ('business', 'PERSON', 'Individual person', 0.9, 'manual'),
    ('business', 'TEAM', 'Group of people working together', 0.9, 'manual'),
    ('business', 'PROJECT', 'Business project or initiative', 0.9, 'manual'),
    ('business', 'BUDGET', 'Financial allocation', 0.9, 'manual'),
    ('legal', 'CONTRACT', 'Legal agreement', 0.9, 'manual'),
    ('legal', 'PARTY', 'Legal entity in agreement', 0.9, 'manual'),
    ('legal', 'CLAUSE', 'Contract clause or provision', 0.9, 'manual');

INSERT INTO domain_relationship_types (domain, relationship_type, source_verb, description, confidence_score, source) VALUES
    ('technical', 'INTEGRATES_WITH', 'integrates', 'System integration relationship', 0.9, 'verb_extraction'),
    ('technical', 'DEPENDS_ON', 'depends', 'Dependency relationship', 0.9, 'verb_extraction'),
    ('technical', 'CALLS', 'calls', 'Function or API call', 0.9, 'verb_extraction'),
    ('technical', 'RETURNS', 'returns', 'Function return relationship', 0.9, 'verb_extraction'),
    ('business', 'MANAGES', 'manages', 'Management relationship', 0.9, 'verb_extraction'),
    ('business', 'WORKS_ON', 'works', 'Work assignment relationship', 0.9, 'verb_extraction'),
    ('business', 'ASSIGNED_TO', 'assigned', 'Assignment relationship', 0.9, 'verb_extraction'),
    ('business', 'REPORTS_TO', 'reports', 'Reporting hierarchy', 0.9, 'verb_extraction'),
    ('legal', 'GOVERNED_BY', 'governed', 'Legal governance relationship', 0.9, 'verb_extraction'),
    ('legal', 'BOUND_BY', 'bound', 'Legal obligation relationship', 0.9, 'verb_extraction'),
    ('legal', 'REFERS_TO', 'refers', 'Reference relationship', 0.9, 'verb_extraction');

-- Verification query
SELECT 'Domain-specific fallback types schema created successfully!' as status,
       (SELECT COUNT(*) FROM domain_entity_types) as entity_types_created,
       (SELECT COUNT(*) FROM domain_relationship_types) as relationship_types_created;
