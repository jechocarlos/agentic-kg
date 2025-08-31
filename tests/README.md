# AKG Tests Directory

This directory contains all test files for the Agentic Knowledge Graph (AKG) system.

## Test Files

### Core System Tests
- **`test_models.py`** - Test data models and validation
- **`test_neo4j_manager.py`** - Test Neo4j database operations
- **`test_type_manager.py`** - Test entity/relationship type management
- **`test_extraction.py`** - Test entity and relationship extraction
- **`test_ingestion.py`** - Test document ingestion pipeline

### Feature-Specific Tests
- **`test_dynamic_node_types.py`** - Demo dynamic vs static node labeling
- **`test_supabase_domain_types.py`** - Test Supabase domain type integration
- **`test_supabase_mcp_domain_types.py`** - Test Supabase MCP domain types
- **`test_verb_extraction.py`** - Test verb-focused relationship extraction
- **`test_adaptive_extraction.py`** - Test adaptive document processing
- **`test_extraction_comparison.py`** - Compare extraction approaches

### Utility Files
- **`demo_supabase_mcp_workflow.py`** - Comprehensive Supabase MCP workflow demonstration
- **`test_runner.py`** - Script to run all tests
- **`conftest.py`** - Pytest configuration and fixtures
- **`clear_and_reprocess.py`** - Utility to clear and reprocess data
- **`check_caps.py`** - Verify ALL CAPS relationship compliance

## Running Tests

### Run All Tests
```bash
cd /path/to/akg
python tests/test_runner.py
```

### Run Individual Tests
```bash
cd /path/to/akg
python tests/test_dynamic_node_types.py
python tests/test_supabase_domain_types.py
python tests/demo_supabase_mcp_workflow.py
```

### Run with Pytest (if applicable)
```bash
cd /path/to/akg
pytest tests/
```

## Test Categories

### 1. Unit Tests
Individual component testing:
- `test_models.py`
- `test_type_manager.py`

### 2. Integration Tests
Multi-component testing:
- `test_neo4j_manager.py`
- `test_supabase_domain_types.py`

### 3. End-to-End Tests
Full pipeline testing:
- `test_extraction.py`
- `test_ingestion.py`

### 4. Demo/Comparison Tests
Feature demonstrations:
- `test_dynamic_node_types.py` - Compare static vs dynamic node labeling
- `test_adaptive_extraction.py` - Adaptive processing demonstrations
- `test_extraction_comparison.py` - Extraction approach comparisons
- `demo_supabase_mcp_workflow.py` - Complete Supabase MCP workflow demo

### 5. Utility Scripts
Database and system utilities:
- `clear_and_reprocess.py` - Reset and reprocess all data
- `check_caps.py` - Verify relationship naming compliance

## Requirements

### Environment Setup
Ensure you have the virtual environment activated:
```bash
source venv/bin/activate  # On macOS/Linux
```

### Required Services
Some tests require external services:
- **Neo4j**: Required for graph database tests
- **Supabase**: Required for domain type integration tests
- **Google Gemini API**: Required for AI extraction tests

### Environment Variables
Set these for full test coverage:
```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your_password"
export SUPABASE_URL="your_supabase_url"
export SUPABASE_ANON_KEY="your_supabase_key"
export GOOGLE_API_KEY="your_gemini_key"
```

## Test Data

### Sample Documents
Tests use various sample documents:
- Technical specifications
- Business documents
- Legal policies
- Meeting notes

### Graph Data
Tests may create temporary graph data that is cleaned up automatically.

## Adding New Tests

### Naming Convention
- Prefix test files with `test_`
- Use descriptive names: `test_feature_name.py`

### Import Pattern
```python
import sys
import os
from datetime import datetime

# Add the parent directory to access src
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.akg.module import YourClass
```

### Async Test Pattern
```python
import asyncio

async def test_your_feature():
    """Test description."""
    # Your test code here
    pass

if __name__ == "__main__":
    asyncio.run(test_your_feature())
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure the path setup is correct
2. **Service Connection**: Check if required services are running
3. **Environment Variables**: Verify all required variables are set
4. **Virtual Environment**: Make sure venv is activated

### Debug Mode
Add debug prints or use pytest with `-v` flag for verbose output.

## Contributing

When adding new functionality:
1. Write corresponding tests
2. Update this README if needed
3. Ensure tests pass before committing
4. Follow existing patterns and conventions
