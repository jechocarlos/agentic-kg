# Automated Knowledge Graph (AKG)

An intelligent document processing system that automatically extracts entities and relationships from local documents to build a queryable knowledge graph using advanced NLP, Google Gemini, and Neo4j.

## 🎯 Key Features

- **📄 Smart Document Chunking**: Automatically splits large documents into optimal segments for better entity extraction
- **🤖 AI-Powered Extraction**: Uses Google Gemini with SUBJECT-PREDICATE-OBJECT focused prompts
- **🔗 Granular Relationships**: Creates specific, meaningful relationship types instead of generic connections
- **🔤 ALL CAPS Standards**: Enforces uppercase relationship types for consistency (e.g., `WORKS_FOR`, `HAS_BUDGET`)
- **🧠 Dynamic Type Learning**: Automatically discovers and reuses entity/relationship types across documents
- **⚡ Async Processing**: High-performance concurrent document processing
- **📊 Rich Visualization**: Real-time processing feedback with progress indicators
- **🔍 Comprehensive Testing**: 71+ test cases ensuring reliability

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

**What happens during processing:**
1. 📄 **Document Chunking**: Large documents are split into optimal segments (2000 chars with 200 char overlap)
2. 🤖 **AI Extraction**: Each chunk is processed with SUBJECT-PREDICATE-OBJECT focused prompts
3. 🔗 **Relationship Creation**: Generates specific relationship types like `WORKS_FOR`, `HAS_BUDGET`, `MANAGES`
4. 🔤 **Type Standardization**: All relationship types converted to ALL CAPS for consistency
5. 📊 **Graph Building**: Entities and relationships saved to Neo4j with full provenance
6. ✅ **Validation**: Comprehensive testing ensures data quality

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

The system features a sophisticated multi-agent architecture with specialized components:

### Core Agents
1. **📥 Ingestion Agent** - Scans and processes local files with hash-based change detection
2. **🧠 Extraction Agent** - Advanced entity extraction using:
   - **Document Chunking**: Smart segmentation for optimal processing
   - **SPO Extraction**: SUBJECT-PREDICATE-OBJECT focused relationship identification
   - **Dynamic Type Management**: Automatic type discovery and reuse
   - **Fallback Processing**: Pattern-based extraction when AI fails
3. **🔗 Graph Construction Agent** - Builds Neo4j knowledge graph with:
   - **ALL CAPS Relationships**: Standardized relationship type formatting
   - **Deduplication**: Smart entity and relationship merging
   - **Provenance Tracking**: Full data lineage preservation

### Advanced Features
- **⚡ Async Processing**: Concurrent document handling for performance
- **🔄 Type Resolution**: Intelligent entity/relationship type matching
- **📊 Real-time Feedback**: Rich progress indicators and statistics
- **🧪 Comprehensive Testing**: 71+ test cases with 100% pass rate
- **🛠️ Utility Scripts**: Database management and relationship analysis tools

### Data Flow
```
Documents → Chunking → AI Extraction → Type Resolution → Graph Construction → Neo4j
     ↓                                      ↓              ↓
  Supabase ←------ Provenance ←------ Validation ←------ Deduplication
```

## 📁 Project Structure

```
akg/
├── .github/
│   ├── SPECS.md          # Project specifications
│   └── TODO.md           # Task tracking
├── src/akg/
│   ├── agents/           # Processing agents
│   │   ├── extraction.py # Advanced AI extraction with chunking
│   │   ├── ingestion.py  # File processing and monitoring
│   │   └── fallback_extraction.py # Pattern-based backup
│   ├── database/         # Database managers
│   │   ├── neo4j_manager.py      # Graph database operations
│   │   └── supabase_manager.py   # Document storage
│   ├── parsers/          # Document parsers
│   │   └── document_parser.py    # Multi-format parsing
│   ├── config.py         # Configuration management
│   ├── models.py         # Data models
│   ├── types.py          # Type definitions
│   └── main.py           # Application entry point
├── tests/                # Comprehensive test suite
│   ├── test_*.py         # Unit tests (71+ tests)
│   ├── clear_and_reprocess.py # Database utilities
│   └── check_relationships.py # Analysis tools
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

# AI Extraction Settings
MAX_CONCURRENT_DOCUMENTS=5
CHUNK_SIZE=2000           # Optimal chunk size for AI processing
OVERLAP_SIZE=200          # Overlap between chunks for context

# Graph Configuration
SIMILARITY_THRESHOLD=0.8  # Entity matching threshold
PROVENANCE_ENABLED=true   # Track data lineage
MAX_GRAPH_DEPTH=5        # Maximum relationship traversal depth

# Performance Tuning
LOG_LEVEL=INFO           # Logging verbosity
```

## 🧪 Testing & Quality

The system includes comprehensive testing with **71+ test cases**:

```bash
# Run the full test suite
python -m pytest tests/ -v

# Test specific components
python -m pytest tests/test_extraction.py -v
python -m pytest tests/test_neo4j_manager.py -v

# Database utilities
python tests/clear_and_reprocess.py    # Reset and reprocess
python tests/check_relationships.py   # Analyze relationships
```

**Test Coverage:**
- ✅ Entity extraction with chunking
- ✅ Relationship type standardization (ALL CAPS)
- ✅ Neo4j graph operations
- ✅ Type resolution and deduplication
- ✅ Async processing workflows
- ✅ Error handling and fallbacks

## 📖 Example Usage

The system comes with sample documents that demonstrate advanced extraction capabilities:

### Processing Examples

**1. Meeting Notes → Knowledge Graph**
```
Input: "Sarah Johnson manages Project Alpha with a $500,000 budget..."
Output: 
- Entities: Sarah Johnson (Person), Project Alpha (Project), $500,000 (Money)
- Relationships: Sarah Johnson -MANAGES-> Project Alpha, Project Alpha -HAS_BUDGET-> $500,000
```

**2. Contract Documents → Structured Data**
```
Input: "TechCorp Solutions Inc. represented by Michael Thompson..."
Output:
- Entities: TechCorp Solutions Inc. (Company), Michael Thompson (Person)
- Relationships: TechCorp Solutions Inc. -REPRESENTED_BY-> Michael Thompson
```

**3. Document Chunking in Action**
- Large documents automatically split into 2000-character segments
- 200-character overlap maintains context between chunks
- Each chunk processed independently for maximum granularity
- Results merged with intelligent deduplication

### Relationship Types Generated
The system creates specific, meaningful relationships:
- **Professional**: `WORKS_FOR`, `MANAGES`, `REPORTS_TO`, `EMPLOYS`
- **Financial**: `HAS_BUDGET`, `ALLOCATED_BUDGET`, `HAS_COST`
- **Temporal**: `OCCURRED_ON`, `SCHEDULED_FOR`, `DEADLINE_IS`
- **Contractual**: `INVOLVES_COMPANY`, `REPRESENTED_BY`, `INCLUDES_SERVICE`
- **Technical**: `USES`, `DEPLOYED_ON`, `DEVELOPED`, `REQUIRES`

### Database Output
**Neo4j Graph Statistics:**
- Entities: 91+ with 19+ types
- Relationships: 173+ with 40+ specific types  
- All relationship types in standardized ALL CAPS format

## 🔍 What's Implemented

✅ **Core Functionality Complete:**
- ✅ Advanced document chunking for optimal AI processing
- ✅ SUBJECT-PREDICATE-OBJECT focused entity extraction
- ✅ ALL CAPS standardized relationship types
- ✅ Dynamic type discovery and intelligent reuse
- ✅ Neo4j knowledge graph construction with provenance
- ✅ Async processing with rich progress feedback
- ✅ Comprehensive test suite (71+ tests, 100% pass rate)
- ✅ Database management utilities
- ✅ Error handling and fallback mechanisms

🚧 **Future Enhancements:**
- [ ] Web interface for graph visualization
- [ ] Advanced querying capabilities with natural language
- [ ] Multi-source document ingestion (SharePoint, Confluence)
- [ ] Real-time collaboration features
- [ ] Advanced conflict resolution workflows

## 🛠️ Utility Commands

```bash
# Process documents with detailed output
python run.py

# Clear database and reprocess everything
python tests/clear_and_reprocess.py

# Analyze relationship patterns
python tests/check_relationships.py

# Run comprehensive tests
python -m pytest tests/ -v

# Check relationship type compliance (ALL CAPS)
python check_caps.py
```

## 📝 Technical Notes

### Advanced Features
- **Smart Chunking**: Documents split at sentence boundaries to preserve context
- **Type Resolution**: Fuzzy matching prevents duplicate entity/relationship types
- **Provenance Tracking**: Full data lineage from source documents to graph nodes
- **Error Recovery**: Graceful fallback to pattern-based extraction when AI fails
- **Performance**: Async processing handles multiple documents concurrently

### Database Design
- **Neo4j**: Stores entities and relationships with full property sets
- **Supabase**: Document storage with metadata and processing status
- **Type Management**: Dynamic schema evolution based on document content
- **Relationship Standards**: ALL CAPS enforced for consistency and query performance

### Quality Assurance
- **71+ Test Cases**: Comprehensive coverage of all major functionality
- **Async Testing**: Proper mocking for database operations
- **Error Scenarios**: Tests for failure modes and recovery
- **Performance Tests**: Validation of chunking and processing efficiency

For detailed technical documentation and API references, see the test files in `/tests` directory which serve as living documentation of the system's capabilities.
