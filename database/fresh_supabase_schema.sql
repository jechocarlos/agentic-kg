-- Fresh AKG Database Schema for Supabase (Document Storage Only)
-- This script drops all existing tables and recreates them from scratch
-- Entities and relationships are stored in Neo4j
-- Run this script in your Supabase SQL editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop all existing tables and views (in correct order to avoid dependency issues)
DROP VIEW IF EXISTS document_processing_summary CASCADE;
DROP VIEW IF EXISTS processing_stats CASCADE;
DROP VIEW IF EXISTS entity_summary CASCADE;
DROP VIEW IF EXISTS relationship_summary CASCADE;

DROP TABLE IF EXISTS system_logs CASCADE;
DROP TABLE IF EXISTS document_chunks CASCADE;
DROP TABLE IF EXISTS extraction_jobs CASCADE;
DROP TABLE IF EXISTS conflict_resolutions CASCADE;
DROP TABLE IF EXISTS extraction_results CASCADE;
DROP TABLE IF EXISTS provenance CASCADE;
DROP TABLE IF EXISTS relationships CASCADE;
DROP TABLE IF EXISTS entities CASCADE;
DROP TABLE IF EXISTS documents CASCADE;

-- Create documents table for document storage and metadata
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_system TEXT NOT NULL DEFAULT 'local_files',
    source_path TEXT NOT NULL UNIQUE,
    document_type TEXT NOT NULL,
    file_size BIGINT,
    file_hash TEXT, -- For detecting changes
    metadata JSONB DEFAULT '{}',
    processed_at TIMESTAMPTZ,
    processing_status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create extraction_jobs table for tracking processing jobs
CREATE TABLE extraction_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending', -- pending, running, completed, failed
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    processing_time_seconds FLOAT,
    entities_extracted INTEGER DEFAULT 0,
    relationships_extracted INTEGER DEFAULT 0,
    error_message TEXT,
    extraction_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create document_chunks table for storing text chunks (if needed for vector embeddings later)
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER,
    char_count INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create system_logs table for application logging
CREATE TABLE system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level TEXT NOT NULL, -- INFO, WARNING, ERROR, DEBUG
    message TEXT NOT NULL,
    component TEXT, -- ingestion, extraction, neo4j, etc.
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX idx_documents_source_path ON documents(source_path);
CREATE INDEX idx_documents_document_type ON documents(document_type);
CREATE INDEX idx_documents_processing_status ON documents(processing_status);
CREATE INDEX idx_documents_created_at ON documents(created_at);
CREATE INDEX idx_documents_file_hash ON documents(file_hash);

CREATE INDEX idx_extraction_jobs_document_id ON extraction_jobs(document_id);
CREATE INDEX idx_extraction_jobs_status ON extraction_jobs(status);
CREATE INDEX idx_extraction_jobs_created_at ON extraction_jobs(created_at);

CREATE INDEX idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_document_chunks_chunk_index ON document_chunks(chunk_index);

CREATE INDEX idx_system_logs_level ON system_logs(level);
CREATE INDEX idx_system_logs_component ON system_logs(component);
CREATE INDEX idx_system_logs_created_at ON system_logs(created_at);

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

-- Create RLS (Row Level Security) policies
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE extraction_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_logs ENABLE ROW LEVEL SECURITY;

-- Create policies (allowing all operations for development)
CREATE POLICY "Enable all access for development" ON documents FOR ALL USING (true);
CREATE POLICY "Enable all access for development" ON extraction_jobs FOR ALL USING (true);
CREATE POLICY "Enable all access for development" ON document_chunks FOR ALL USING (true);
CREATE POLICY "Enable all access for development" ON system_logs FOR ALL USING (true);

-- Create useful views for monitoring
CREATE VIEW document_processing_summary AS
SELECT 
    d.id,
    d.title,
    d.document_type,
    d.processing_status,
    d.created_at,
    d.processed_at,
    ej.entities_extracted,
    ej.relationships_extracted,
    ej.processing_time_seconds,
    CASE 
        WHEN d.processing_status = 'completed' AND d.processed_at IS NOT NULL 
        THEN EXTRACT(EPOCH FROM (d.processed_at - d.created_at)) 
        ELSE NULL 
    END as total_processing_time_seconds
FROM documents d
LEFT JOIN extraction_jobs ej ON d.id = ej.document_id AND ej.status = 'completed'
ORDER BY d.created_at DESC;

CREATE VIEW processing_stats AS
SELECT 
    COUNT(*) as total_documents,
    COUNT(*) FILTER (WHERE processing_status = 'completed') as completed_documents,
    COUNT(*) FILTER (WHERE processing_status = 'failed') as failed_documents,
    COUNT(*) FILTER (WHERE processing_status = 'pending') as pending_documents,
    COUNT(*) FILTER (WHERE processing_status = 'processing') as processing_documents,
    COALESCE(SUM(ej.entities_extracted), 0) as total_entities_extracted,
    COALESCE(SUM(ej.relationships_extracted), 0) as total_relationships_extracted,
    COALESCE(AVG(ej.processing_time_seconds), 0) as avg_processing_time_seconds
FROM documents d
LEFT JOIN extraction_jobs ej ON d.id = ej.document_id AND ej.status = 'completed';

-- Insert a test record to verify everything works
INSERT INTO documents (title, content, source_path, document_type, metadata) 
VALUES (
    'Test Document', 
    'This is a test document to verify the schema is working correctly.', 
    '/test/path/test.md', 
    'markdown',
    '{"test": true}'
);

-- Show final status
SELECT 'AKG Supabase schema created successfully!' as status;
