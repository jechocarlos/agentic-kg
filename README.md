# Automated Knowledge Graph (AKG)

An intelligent document processing system that automatically extracts entities and relationships from local documents to build a queryable knowledge graph using LlamaParse, LangGraph, Google Gemini, and Neo4j.

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```env
# Required credentials
GOOGLE_API_KEY=your_google_gemini_api_key_here
LLAMA_CLOUD_API_KEY=your_llamaparse_api_key_here
NEO4J_PASSWORD=your_neo4j_password_here

# Supabase Database (replaces static models)
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_API_KEY=your_supabase_api_key_here

# Local file configuration
DOCUMENTS_INPUT_DIR=./documents
```

### 3. Setup Supabase Database

1. Create a new project at [Supabase](https://supabase.com)
2. Go to SQL Editor in your Supabase dashboard
3. Run the schema script:
   ```sql
   -- Copy and paste the contents of database/supabase_schema.sql
   ```
4. Test your database connection:
   ```bash
   python setup_database.py
   ```

### 4. Add Your Documents

Place your documents in the configured directory (default: `./documents/`):

```bash
# Example documents are already provided
ls documents/
# sample_policy.md
# meeting_notes_project_alpha.md
# contract_amendment_vendor.md
```

Supported formats:
- PDF (`.pdf`)
- Word Documents (`.docx`)
- Text files (`.txt`, `.md`)
- HTML (`.html`)
- PowerPoint (`.pptx`)
- Excel (`.xlsx`)

### 5. Run the System

```bash
# Process all documents once
python run.py

# Or use watch mode for continuous processing
WATCH_DIRECTORY=true python run.py
```

## 📋 Getting API Keys

### Google Gemini API Key
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add it to your `.env` file as `GOOGLE_API_KEY`

### LlamaParse API Key
1. Sign up at [LlamaParse](https://cloud.llamaindex.ai/)
2. Get your API key from the dashboard
3. Add it to your `.env` file as `LLAMA_CLOUD_API_KEY`

### Supabase Setup
1. Create a project at [Supabase](https://supabase.com)
2. Go to Settings > API in your dashboard
3. Copy your project URL and "anon public" key
4. Add them to your `.env` file as `SUPABASE_URL` and `SUPABASE_API_KEY`
5. Run the database schema: Copy `database/supabase_schema.sql` to your Supabase SQL editor

### Neo4j Setup
1. Install Neo4j Desktop or use Neo4j Aura
2. Create a database
3. Set your password in `.env` as `NEO4J_PASSWORD`

## 🏗️ Architecture

The system consists of several specialized agents:

1. **Ingestion Agent** - Scans and processes local files
2. **Extraction Agent** - Uses Gemini for NER and relationship extraction
3. **Schema Agent** - Manages dynamic ontology evolution
4. **Validation Agent** - Handles conflicts and duplicates
5. **Graph Construction Agent** - Builds Neo4j knowledge graph
6. **Query Agent** - Enables intelligent graph querying

## 📁 Project Structure

```
akg/
├── .github/
│   ├── SPECS.md          # Project specifications
│   └── TODO.md           # Task tracking
├── src/akg/
│   ├── agents/           # Processing agents
│   ├── parsers/          # Document parsers
│   ├── config.py         # Configuration management
│   ├── models.py         # Data models
│   └── main.py           # Application entry point
├── documents/            # Input documents directory
├── .env.example          # Environment template
├── requirements.txt      # Python dependencies
└── run.py               # CLI runner
```

## 🔧 Configuration

Key configuration options in `.env`:

```env
# Document Processing
DOCUMENTS_INPUT_DIR=./documents
SUPPORTED_FILE_TYPES=pdf,docx,txt,md,html,pptx,xlsx
WATCH_DIRECTORY=true
RECURSIVE_SCAN=true

# Processing Limits
MAX_CONCURRENT_DOCUMENTS=5
CHUNK_SIZE=1000

# Graph Configuration
SIMILARITY_THRESHOLD=0.8
PROVENANCE_ENABLED=true
```

## 📖 Example Usage

The system comes with sample documents that demonstrate:

1. **Policy Document** - Shows entity extraction for policies, approvers, and dates
2. **Meeting Notes** - Extracts participants, decisions, and action items
3. **Contract Amendment** - Identifies parties, financial terms, and approvals

## 🔍 What's Next

This is the initial local file ingestion setup. The full system will include:

- [ ] Entity extraction with Google Gemini
- [ ] LangGraph workflow orchestration
- [ ] Neo4j knowledge graph construction
- [ ] Intelligent querying capabilities
- [ ] Web interface for graph visualization

## 📝 Notes

- The system currently focuses on local file processing
- LlamaParse integration provides advanced PDF and document parsing
- The architecture supports easy extension to web-based document sources
- All processing includes provenance tracking for data lineage

For detailed technical documentation, see the `/docs` directory (to be created as development progresses).
