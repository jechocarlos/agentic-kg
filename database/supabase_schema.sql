-- AKG Database Schema for Supabase
-- Run this script in your Supabase SQL editor to create the required tables

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_system TEXT NOT NULL,
    source_path TEXT NOT NULL UNIQUE,
    document_type TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create entities table
CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    properties JSONB DEFAULT '{}',
    aliases TEXT[] DEFAULT '{}',
    confidence_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create relationships table
CREATE TABLE IF NOT EXISTS relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    source_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,
    properties JSONB DEFAULT '{}',
    confidence_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create provenance table for tracking data lineage
CREATE TABLE IF NOT EXISTS provenance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    relationship_id UUID REFERENCES relationships(id) ON DELETE CASCADE,
    source_system TEXT NOT NULL,
    extraction_timestamp TIMESTAMPTZ DEFAULT NOW(),
    confidence_score FLOAT DEFAULT 0.0,
    page_number INTEGER,
    paragraph_index INTEGER,
    extractor_version TEXT DEFAULT '1.0',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create extraction_results table for tracking processing results
CREATE TABLE IF NOT EXISTS extraction_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    processing_time FLOAT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    extraction_metadata JSONB DEFAULT '{}',
    entities_count INTEGER DEFAULT 0,
    relationships_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create conflict_resolutions table for handling conflicts
CREATE TABLE IF NOT EXISTS conflict_resolutions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conflict_type TEXT NOT NULL,
    description TEXT NOT NULL,
    conflicting_entity_ids UUID[],
    conflicting_relationship_ids UUID[],
    resolution_strategy TEXT,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    human_review_required BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_documents_source_path ON documents(source_path);
CREATE INDEX IF NOT EXISTS idx_documents_document_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);

CREATE INDEX IF NOT EXISTS idx_entities_document_id ON entities(document_id);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_entity_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_name_gin ON entities USING gin(to_tsvector('english', name));

CREATE INDEX IF NOT EXISTS idx_relationships_document_id ON relationships(document_id);
CREATE INDEX IF NOT EXISTS idx_relationships_source_entity_id ON relationships(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target_entity_id ON relationships(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(relationship_type);

CREATE INDEX IF NOT EXISTS idx_provenance_document_id ON provenance(document_id);
CREATE INDEX IF NOT EXISTS idx_provenance_entity_id ON provenance(entity_id);
CREATE INDEX IF NOT EXISTS idx_provenance_relationship_id ON provenance(relationship_id);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_entities_updated_at BEFORE UPDATE ON entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_relationships_updated_at BEFORE UPDATE ON relationships
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create RLS (Row Level Security) policies
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE provenance ENABLE ROW LEVEL SECURITY;
ALTER TABLE extraction_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE conflict_resolutions ENABLE ROW LEVEL SECURITY;

-- Create policies (adjust these based on your authentication needs)
CREATE POLICY "Enable read access for all users" ON documents FOR SELECT USING (true);
CREATE POLICY "Enable insert for all users" ON documents FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for all users" ON documents FOR UPDATE USING (true);
CREATE POLICY "Enable delete for all users" ON documents FOR DELETE USING (true);

CREATE POLICY "Enable read access for all users" ON entities FOR SELECT USING (true);
CREATE POLICY "Enable insert for all users" ON entities FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for all users" ON entities FOR UPDATE USING (true);
CREATE POLICY "Enable delete for all users" ON entities FOR DELETE USING (true);

CREATE POLICY "Enable read access for all users" ON relationships FOR SELECT USING (true);
CREATE POLICY "Enable insert for all users" ON relationships FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for all users" ON relationships FOR UPDATE USING (true);
CREATE POLICY "Enable delete for all users" ON relationships FOR DELETE USING (true);

CREATE POLICY "Enable read access for all users" ON provenance FOR SELECT USING (true);
CREATE POLICY "Enable insert for all users" ON provenance FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for all users" ON provenance FOR UPDATE USING (true);
CREATE POLICY "Enable delete for all users" ON provenance FOR DELETE USING (true);

CREATE POLICY "Enable read access for all users" ON extraction_results FOR SELECT USING (true);
CREATE POLICY "Enable insert for all users" ON extraction_results FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for all users" ON extraction_results FOR UPDATE USING (true);
CREATE POLICY "Enable delete for all users" ON extraction_results FOR DELETE USING (true);

CREATE POLICY "Enable read access for all users" ON conflict_resolutions FOR SELECT USING (true);
CREATE POLICY "Enable insert for all users" ON conflict_resolutions FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for all users" ON conflict_resolutions FOR UPDATE USING (true);
CREATE POLICY "Enable delete for all users" ON conflict_resolutions FOR DELETE USING (true);

-- Create some useful views
CREATE OR REPLACE VIEW entity_summary AS
SELECT 
    entity_type,
    COUNT(*) as count,
    AVG(confidence_score) as avg_confidence
FROM entities 
GROUP BY entity_type
ORDER BY count DESC;

CREATE OR REPLACE VIEW relationship_summary AS
SELECT 
    relationship_type,
    COUNT(*) as count,
    AVG(confidence_score) as avg_confidence
FROM relationships 
GROUP BY relationship_type
ORDER BY count DESC;

CREATE OR REPLACE VIEW document_processing_summary AS
SELECT 
    d.id,
    d.title,
    d.document_type,
    d.created_at,
    COUNT(DISTINCT e.id) as entity_count,
    COUNT(DISTINCT r.id) as relationship_count,
    AVG(e.confidence_score) as avg_entity_confidence,
    AVG(r.confidence_score) as avg_relationship_confidence
FROM documents d
LEFT JOIN entities e ON d.id = e.document_id
LEFT JOIN relationships r ON d.id = r.document_id
GROUP BY d.id, d.title, d.document_type, d.created_at
ORDER BY d.created_at DESC;
