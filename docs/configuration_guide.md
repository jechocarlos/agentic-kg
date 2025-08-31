# Configuration Guide

## Overview

The AKG system uses environment variables for configuration management through Pydantic Settings. All configuration is centralized in `src/akg/config.py` with support for `.env` files.

## Environment Setup

### 1. Environment File

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

### 2. Required Configuration

#### Google Gemini API (Required)

The primary AI service for entity extraction.

```bash
# Get from: https://makersuite.google.com/app/apikey
GOOGLE_API_KEY=your_google_gemini_api_key_here

# Optional: For specific project configurations
GOOGLE_PROJECT_ID=your_google_project_id
```

**Setup Steps**:
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key to your `.env` file
4. Test with: `python -c "import google.generativeai as genai; genai.configure(api_key='your_key'); print('✅ API key valid')"`

#### LlamaParse API (Required)

Document parsing service for complex file formats.

```bash
# Get from: https://cloud.llamaindex.ai/
LLAMA_CLOUD_API_KEY=your_llamaparse_api_key_here
```

**Setup Steps**:
1. Sign up at [LlamaParse](https://cloud.llamaindex.ai/)
2. Navigate to API keys section
3. Generate a new API key
4. Add to `.env` file

#### Neo4j Database (Required)

Graph database for entities and relationships.

```bash
# Connection settings
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password_here
NEO4J_DATABASE=neo4j
```

**Setup Options**:

**Option A: Local Installation**
```bash
# Install Neo4j Desktop or Community Edition
# Start database and set password
# Test connection: neo4j-shell -host localhost -port 7687 -username neo4j
```

**Option B: Neo4j Aura Cloud**
```bash
# Create account at https://neo4j.com/aura/
# Create new database instance
# Copy connection URI and credentials
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_generated_password
```

#### Supabase Database (Required)

Document storage and domain type caching.

```bash
# Project settings from Supabase dashboard
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_API_KEY=your_supabase_anon_key_here

# Optional: For admin operations
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

**Setup Steps**:
1. Create project at [Supabase](https://supabase.com)
2. Go to Settings > API
3. Copy Project URL and "anon public" key
4. Apply database schema: `supabase/migrations/20250830_create_domain_types_schema.sql`
5. Test connection: `python tests/demo_supabase_mcp_workflow.py`

### 3. Optional Configuration

#### Application Settings

```bash
# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Performance tuning
MAX_CONCURRENT_DOCUMENTS=5
CHUNK_SIZE=2000
OVERLAP_SIZE=200

# Graph configuration
MAX_GRAPH_DEPTH=5
SIMILARITY_THRESHOLD=0.8
PROVENANCE_ENABLED=true
```

#### File Processing

```bash
# Document input directory
DOCUMENTS_INPUT_DIR=./documents

# Supported file types (comma-separated)
SUPPORTED_FILE_TYPES=pdf,docx,txt,md,html,pptx,xlsx

# File monitoring
WATCH_DIRECTORY=true
RECURSIVE_SCAN=true
```

## Configuration Reference

### Core Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `GOOGLE_API_KEY` | string | Required | Google Gemini API key |
| `LLAMA_CLOUD_API_KEY` | string | Required | LlamaParse API key |
| `NEO4J_PASSWORD` | string | Required | Neo4j database password |
| `SUPABASE_URL` | string | Required | Supabase project URL |
| `SUPABASE_API_KEY` | string | Required | Supabase API key |

### Database Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `NEO4J_URI` | string | `bolt://localhost:7687` | Neo4j connection URI |
| `NEO4J_USERNAME` | string | `neo4j` | Neo4j username |
| `NEO4J_DATABASE` | string | `neo4j` | Neo4j database name |
| `SUPABASE_SERVICE_ROLE_KEY` | string | None | Admin API key |

### Processing Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LOG_LEVEL` | string | `INFO` | Logging verbosity |
| `MAX_CONCURRENT_DOCUMENTS` | int | 5 | Parallel processing limit |
| `CHUNK_SIZE` | int | 2000 | Document chunk size (chars) |
| `OVERLAP_SIZE` | int | 200 | Chunk overlap (chars) |

### Graph Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MAX_GRAPH_DEPTH` | int | 5 | Maximum traversal depth |
| `SIMILARITY_THRESHOLD` | float | 0.8 | Entity matching threshold |
| `PROVENANCE_ENABLED` | bool | true | Track data lineage |

### File Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DOCUMENTS_INPUT_DIR` | string | `./documents` | Input directory path |
| `SUPPORTED_FILE_TYPES` | string | `pdf,docx,txt,md,html,pptx,xlsx` | File type filter |
| `WATCH_DIRECTORY` | bool | true | Monitor for changes |
| `RECURSIVE_SCAN` | bool | true | Scan subdirectories |

## Configuration Validation

### Validation Script

Test your configuration with:

```python
#!/usr/bin/env python3
"""Configuration validation script."""

import sys
sys.path.append('src')

from akg.config import config

def validate_config():
    """Validate all configuration settings."""
    
    print("🔧 AKG Configuration Validation")
    print("=" * 40)
    
    # Test Google Gemini
    try:
        import google.generativeai as genai
        genai.configure(api_key=config.google_api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        print("✅ Google Gemini API: Valid")
    except Exception as e:
        print(f"❌ Google Gemini API: {e}")
        return False
    
    # Test Neo4j connection
    try:
        from akg.database.neo4j_manager import Neo4jManager
        import asyncio
        
        async def test_neo4j():
            neo4j = Neo4jManager()
            await neo4j.initialize()
            await neo4j.close()
            return True
            
        result = asyncio.run(test_neo4j())
        print("✅ Neo4j Database: Connected")
    except Exception as e:
        print(f"❌ Neo4j Database: {e}")
        return False
    
    # Test Supabase connection
    try:
        from akg.database.supabase_manager import SupabaseManager
        
        async def test_supabase():
            supabase = SupabaseManager(config.supabase_url, config.supabase_api_key)
            await supabase.initialize()
            return True
            
        result = asyncio.run(test_supabase())
        print("✅ Supabase Database: Connected")
    except Exception as e:
        print(f"❌ Supabase Database: {e}")
        return False
    
    # Test file directory
    try:
        from pathlib import Path
        doc_dir = Path(config.documents_input_dir)
        if doc_dir.exists():
            print(f"✅ Documents Directory: {doc_dir.absolute()}")
        else:
            print(f"⚠️ Documents Directory: {doc_dir.absolute()} (will be created)")
            doc_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"❌ Documents Directory: {e}")
        return False
    
    print("\n🎉 All configuration valid!")
    return True

if __name__ == "__main__":
    if validate_config():
        sys.exit(0)
    else:
        sys.exit(1)
```

Save as `validate_config.py` and run:

```bash
python validate_config.py
```

## Environment-Specific Configurations

### Development Environment

```bash
# .env.development
LOG_LEVEL=DEBUG
MAX_CONCURRENT_DOCUMENTS=2
WATCH_DIRECTORY=true
PROVENANCE_ENABLED=true

# Use local databases
NEO4J_URI=bolt://localhost:7687
```

### Testing Environment

```bash
# .env.test
LOG_LEVEL=WARNING
MAX_CONCURRENT_DOCUMENTS=1
WATCH_DIRECTORY=false

# Use test databases
NEO4J_DATABASE=test_akg
SUPABASE_URL=https://test-project.supabase.co
```

### Production Environment

```bash
# .env.production
LOG_LEVEL=INFO
MAX_CONCURRENT_DOCUMENTS=10
CHUNK_SIZE=3000
SIMILARITY_THRESHOLD=0.85

# Use production databases
NEO4J_URI=neo4j+s://production.databases.neo4j.io
SUPABASE_URL=https://prod-project.supabase.co
```

## Performance Tuning

### Document Processing

```bash
# Large documents: Increase chunk size
CHUNK_SIZE=3000
OVERLAP_SIZE=300

# Many small documents: Increase concurrency
MAX_CONCURRENT_DOCUMENTS=10

# Memory constrained: Reduce concurrency
MAX_CONCURRENT_DOCUMENTS=2
```

### AI Service Optimization

```bash
# Google Gemini rate limits
# Free tier: 15 requests/minute
# Paid tier: 60 requests/minute
# Adjust MAX_CONCURRENT_DOCUMENTS accordingly
```

### Database Performance

```bash
# Neo4j optimization
# Increase heap size in neo4j.conf:
# server.memory.heap.initial_size=2G
# server.memory.heap.max_size=4G

# Supabase optimization
# Use connection pooling for high-traffic applications
```

## Security Considerations

### API Key Management

```bash
# Use environment-specific keys
GOOGLE_API_KEY_DEV=dev_key_here
GOOGLE_API_KEY_PROD=prod_key_here

# Rotate keys regularly
# Monitor API usage and quotas
# Use least-privilege service accounts
```

### Database Security

```bash
# Neo4j: Use strong passwords and TLS
NEO4J_URI=neo4j+s://secure-host:7687

# Supabase: Use RLS policies and service role keys judiciously
SUPABASE_SERVICE_ROLE_KEY=only_for_admin_operations
```

### File System Security

```bash
# Restrict document directory permissions
chmod 750 ./documents

# Use absolute paths for clarity
DOCUMENTS_INPUT_DIR=/secure/documents/path
```

## Troubleshooting

### Common Configuration Issues

#### 1. Missing API Keys

```bash
# Error: Configuration validation failed
# Solution: Check .env file exists and has correct format
cat .env | grep API_KEY
```

#### 2. Database Connection Issues

```bash
# Neo4j connection refused
# Check: Neo4j is running on specified port
netstat -an | grep 7687

# Supabase 403 errors
# Check: API key has correct permissions
# Check: RLS policies allow access
```

#### 3. File Permission Issues

```bash
# Permission denied errors
# Check: Directory permissions and ownership
ls -la ./documents
sudo chown -R $USER:$USER ./documents
```

#### 4. Memory Issues

```bash
# Out of memory errors
# Reduce: MAX_CONCURRENT_DOCUMENTS
# Reduce: CHUNK_SIZE
# Increase: System memory or swap
```

### Configuration Testing Commands

```bash
# Test individual components
python -c "from src.akg.config import config; print(config.google_api_key[:10] + '...')"
python -c "from src.akg.database.neo4j_manager import Neo4jManager; import asyncio; asyncio.run(Neo4jManager().initialize())"
python -c "from src.akg.database.supabase_manager import SupabaseManager; import asyncio; asyncio.run(SupabaseManager('url', 'key').initialize())"

# Full system test
python run.py --dry-run  # If supported
python tests/demo_supabase_mcp_workflow.py
```

## Configuration Best Practices

1. **Use Environment Files**: Keep secrets out of code
2. **Validate Early**: Test configuration on startup
3. **Document Defaults**: Provide sensible defaults for optional settings
4. **Environment Separation**: Use different configs for dev/test/prod
5. **Security First**: Never commit secrets to version control
6. **Monitor Usage**: Track API quotas and database performance
7. **Regular Updates**: Keep API keys and credentials rotated

This configuration guide provides comprehensive setup and tuning information for all AKG system components.
