-- Migration script to update existing Supabase tables for AKG system
-- Run this in your Supabase SQL editor to add missing columns

-- First, let's add missing columns to the documents table if they don't exist
DO $$ 
BEGIN
    -- Add processing_status column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'documents' AND column_name = 'processing_status') THEN
        ALTER TABLE documents ADD COLUMN processing_status TEXT DEFAULT 'pending';
    END IF;
    
    -- Add file_size column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'documents' AND column_name = 'file_size') THEN
        ALTER TABLE documents ADD COLUMN file_size BIGINT;
    END IF;
    
    -- Add file_hash column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'documents' AND column_name = 'file_hash') THEN
        ALTER TABLE documents ADD COLUMN file_hash TEXT;
    END IF;
    
    -- Add error_message column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'documents' AND column_name = 'error_message') THEN
        ALTER TABLE documents ADD COLUMN error_message TEXT;
    END IF;
    
    -- Add source_system column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'documents' AND column_name = 'source_system') THEN
        ALTER TABLE documents ADD COLUMN source_system TEXT DEFAULT 'local_files';
    END IF;
END $$;

-- Create extraction_jobs table if it doesn't exist
CREATE TABLE IF NOT EXISTS extraction_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    processing_time_seconds FLOAT,
    entities_extracted INTEGER DEFAULT 0,
    relationships_extracted INTEGER DEFAULT 0,
    error_message TEXT,
    extraction_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create document_chunks table if it doesn't exist
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER,
    char_count INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create system_logs table if it doesn't exist
CREATE TABLE IF NOT EXISTS system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    component TEXT,
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for new tables
CREATE INDEX IF NOT EXISTS idx_extraction_jobs_document_id ON extraction_jobs(document_id);
CREATE INDEX IF NOT EXISTS idx_extraction_jobs_status ON extraction_jobs(status);
CREATE INDEX IF NOT EXISTS idx_extraction_jobs_created_at ON extraction_jobs(created_at);

CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_chunk_index ON document_chunks(chunk_index);

CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_component ON system_logs(component);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at);

-- Add new indexes for documents table
CREATE INDEX IF NOT EXISTS idx_documents_processing_status ON documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash);

-- Enable RLS for new tables
ALTER TABLE extraction_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_logs ENABLE ROW LEVEL SECURITY;

-- Create policies for new tables
CREATE POLICY "Enable all access for development" ON extraction_jobs FOR ALL USING (true);
CREATE POLICY "Enable all access for development" ON document_chunks FOR ALL USING (true);
CREATE POLICY "Enable all access for development" ON system_logs FOR ALL USING (true);

-- Create or replace the processing stats view
CREATE OR REPLACE VIEW processing_stats AS
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

-- Create or replace the document processing summary view
CREATE OR REPLACE VIEW document_processing_summary AS
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
