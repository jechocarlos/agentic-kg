# Automated Knowledge Graph (AKG) Specifications

## Project Overview
An intelligent document processing system that automatically extracts entities and relationships from internal documents to build a queryable knowledge graph.

## Core Architecture

### Technology Stack
- **Document Processing**: LlamaParse for PDF/document parsing
- **LLM**: Google Gemini for entity extraction and relationship identification
- **Workflow Orchestration**: LangGraph for agent coordination
- **Graph Database**: Neo4j for knowledge graph storage
- **Environment**: Python with async support

### Agent Flow
1. **Ingestion Agent**: Document collection from various sources
2. **Extraction Agent**: NER and relationship extraction using Gemini
3. **Schema Agent**: Dynamic ontology management
4. **Validation Agent**: Duplicate detection and conflict resolution
5. **Graph Construction Agent**: Neo4j graph building with provenance
6. **Maintenance Agent**: Periodic updates and entity evolution tracking
7. **Query Agent**: Intelligent graph querying for RAG

## Key Features
- Multi-source document ingestion (SharePoint, Confluence, Jira, emails)
- Dynamic schema evolution based on document content
- Provenance tracking for fact verification
- Conflict resolution with human review workflows
- Intelligent querying beyond keyword search

## Success Criteria
- Successfully extract entities and relationships from various document types
- Build coherent knowledge graph with proper provenance
- Handle conflicts and duplicates intelligently
- Enable natural language queries about organizational knowledge

## Security & Privacy
- Secure credential management via .env
- Data lineage and audit trails
- Configurable access controls
