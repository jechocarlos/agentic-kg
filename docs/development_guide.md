# Development Guide

## Getting Started

### Development Environment Setup

#### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/jechocarlos/agentic-kg.git
cd agentic-kg

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-asyncio black isort mypy pre-commit
```

#### 2. IDE Configuration

**VS Code (Recommended)**

Create `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "python.analysis.typeCheckingMode": "basic"
}
```

#### 3. Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Test hooks
pre-commit run --all-files
```

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203]
```

## Project Architecture

### Directory Structure

```
akg/
├── src/akg/              # Core application code
│   ├── agents/           # Processing agents
│   ├── database/         # Database managers
│   ├── parsers/          # Document parsers
│   ├── config.py         # Configuration management
│   ├── models.py         # Data models
│   ├── types.py          # Type definitions
│   └── main.py           # Application entry point
├── tests/                # Test suite
├── docs/                 # Documentation
├── supabase/             # Database migrations
├── documents/            # Input documents
└── requirements.txt      # Dependencies
```

### Code Organization Principles

1. **Agent-Based Architecture**: Specialized agents for different concerns
2. **Database Separation**: Neo4j for graph, Supabase for documents
3. **Async-First**: All I/O operations are asynchronous
4. **Type Safety**: Pydantic models for data validation
5. **Configuration Management**: Environment-based configuration
6. **Rich Logging**: Structured logging with Rich console output

## Development Workflow

### 1. Feature Development

#### Branch Strategy

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: add new feature description"

# Push and create PR
git push origin feature/your-feature-name
```

#### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
feat: add new extraction algorithm
fix: resolve Neo4j connection timeout
docs: update API documentation
test: add unit tests for type manager
refactor: simplify entity extraction logic
perf: optimize document chunking
```

### 2. Testing Workflow

#### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_extraction.py -v

# Run with coverage
python -m pytest tests/ --cov=src/akg --cov-report=html

# Run async tests specifically
python -m pytest tests/test_neo4j_manager.py -v
```

#### Writing Tests

**Test File Structure**:
```python
import asyncio
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from akg.agents.extraction import EntityExtractionAgent
from akg.models import Document, Entity, Relationship

class TestEntityExtractionAgent:
    """Test cases for EntityExtractionAgent."""
    
    @pytest.fixture
    async def extraction_agent(self):
        """Create extraction agent for testing."""
        agent = EntityExtractionAgent()
        yield agent
        # Cleanup if needed
    
    @pytest.mark.asyncio
    async def test_extract_entities_and_relationships(self, extraction_agent):
        """Test entity extraction from document."""
        # Create test document
        document = Document(
            id="test-doc",
            title="Test Document",
            content="John works for Acme Corp.",
            source_path="test.txt",
            document_type="text"
        )
        
        # Extract entities and relationships
        entities, relationships = await extraction_agent.extract_entities_and_relationships(document)
        
        # Assertions
        assert len(entities) >= 2
        assert len(relationships) >= 1
        assert any(e.name == "John" for e in entities)
        assert any(e.name == "Acme Corp" for e in entities)
```

#### Test Categories

1. **Unit Tests**: Test individual methods in isolation
2. **Integration Tests**: Test component interactions
3. **End-to-End Tests**: Test complete workflows
4. **Performance Tests**: Test performance characteristics

### 3. Adding New Features

#### Adding a New Agent

1. **Create Agent File**:
```python
# src/akg/agents/new_agent.py
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class NewAgent:
    """Agent for new functionality."""
    
    def __init__(self, config=None):
        self.config = config
        
    async def process(self, input_data: Any) -> Any:
        """Main processing method."""
        logger.info("Processing with NewAgent")
        # Implementation here
        return result
```

2. **Add Configuration**:
```python
# src/akg/config.py - Add new settings
class AKGConfig(BaseSettings):
    # ... existing settings ...
    
    # New agent settings
    new_agent_enabled: bool = Field(True, alias="NEW_AGENT_ENABLED")
    new_agent_param: str = Field("default", alias="NEW_AGENT_PARAM")
```

3. **Write Tests**:
```python
# tests/test_new_agent.py
import pytest
from src.akg.agents.new_agent import NewAgent

class TestNewAgent:
    @pytest.mark.asyncio
    async def test_process(self):
        agent = NewAgent()
        result = await agent.process("test_input")
        assert result is not None
```

4. **Update Documentation**:
```markdown
# docs/api_reference.md - Add agent documentation
### NewAgent

**Location**: `src/akg/agents/new_agent.py`

Description of agent functionality...
```

#### Adding a New Database Table

1. **Create Migration**:
```sql
-- supabase/migrations/20250831_add_new_table.sql
CREATE TABLE new_table (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_new_table_name ON new_table(name);
```

2. **Update Manager**:
```python
# src/akg/database/supabase_manager.py
async def create_new_record(self, name: str, data: Dict) -> bool:
    """Create record in new table."""
    try:
        result = self.client.table('new_table').insert({
            'name': name,
            'data': data
        }).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to create record: {e}")
        return False
```

3. **Add Model**:
```python
# src/akg/models.py
class NewRecord(BaseModel):
    """Model for new table records."""
    id: str
    name: str
    data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

#### Adding a New File Parser

1. **Create Parser**:
```python
# src/akg/parsers/new_parser.py
from typing import Optional
from ..models import Document

class NewFormatParser:
    """Parser for new file format."""
    
    @staticmethod
    def can_parse(file_path: str) -> bool:
        """Check if file can be parsed."""
        return file_path.endswith('.newformat')
    
    @staticmethod
    async def parse(file_path: str) -> Optional[Document]:
        """Parse file to Document."""
        try:
            # Parse logic here
            return Document(
                id=generate_id(),
                title=extracted_title,
                content=extracted_content,
                source_path=file_path,
                document_type='new_format'
            )
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return None
```

2. **Register Parser**:
```python
# src/akg/parsers/document_parser.py
from .new_parser import NewFormatParser

class DocumentParser:
    def __init__(self):
        self.parsers = [
            # ... existing parsers ...
            NewFormatParser,
        ]
```

## Code Style Guidelines

### Python Style

Follow PEP 8 with Black formatting:

```python
# Good: Clear function names and type hints
async def extract_entities_from_document(
    document: Document, 
    confidence_threshold: float = 0.8
) -> List[Entity]:
    """Extract entities from document with confidence filtering."""
    entities = []
    
    # Process document
    for chunk in self._chunk_document(document):
        chunk_entities = await self._process_chunk(chunk)
        entities.extend(chunk_entities)
    
    # Filter by confidence
    return [e for e in entities if e.confidence_score >= confidence_threshold]

# Good: Descriptive variable names
extraction_start_time = time.time()
high_confidence_entities = filter_by_confidence(entities, 0.9)
relationship_count = len(relationships)

# Good: Clear error handling
try:
    result = await complex_operation()
    logger.info(f"✅ Operation successful: {result}")
    return result
except SpecificException as e:
    logger.error(f"❌ Specific error: {e}")
    return fallback_value
except Exception as e:
    logger.error(f"❌ Unexpected error: {e}")
    raise
```

### Documentation Style

#### Docstring Format

```python
async def complex_method(
    self,
    param1: str,
    param2: List[str],
    param3: Optional[Dict] = None
) -> Tuple[List[Entity], List[Relationship]]:
    """
    One-line summary of method purpose.
    
    Longer description explaining the method's behavior,
    important implementation details, and usage patterns.
    
    Args:
        param1: Description of first parameter
        param2: Description of second parameter
        param3: Optional parameter description with default behavior
        
    Returns:
        Tuple containing:
        - List of extracted entities
        - List of discovered relationships
        
    Raises:
        ValueError: When param1 is empty or invalid
        ConnectionError: When database connection fails
        
    Example:
        >>> agent = EntityExtractionAgent()
        >>> entities, relationships = await agent.complex_method(
        ...     "test_param",
        ...     ["item1", "item2"]
        ... )
        >>> len(entities) > 0
        True
    """
```

#### Code Comments

```python
# Good: Explain why, not what
# Use fuzzy matching to handle slight variations in entity names
similarity_score = fuzz.ratio(candidate_name, existing_name)

# Cache the result to avoid repeated expensive operations
if content_hash not in self._analysis_cache:
    self._analysis_cache[content_hash] = await self._analyze_document(doc)

# Split at sentence boundaries to preserve semantic context
sentences = nltk.sent_tokenize(content)
```

## Performance Guidelines

### Async Programming

```python
# Good: Use async/await for I/O operations
async def process_documents(documents: List[Document]) -> List[ExtractionResult]:
    """Process multiple documents concurrently."""
    semaphore = asyncio.Semaphore(config.max_concurrent_documents)
    
    async def process_single(doc: Document) -> ExtractionResult:
        async with semaphore:
            return await self.extract_entities_and_relationships(doc)
    
    tasks = [process_single(doc) for doc in documents]
    return await asyncio.gather(*tasks, return_exceptions=True)

# Good: Use connection pooling
async def batch_database_operations(operations: List[Operation]) -> List[Result]:
    """Execute database operations in batches."""
    async with self.driver.session() as session:
        async with session.begin_transaction() as tx:
            results = []
            for operation in operations:
                result = await tx.run(operation.query, operation.params)
                results.append(result)
            return results
```

### Memory Management

```python
# Good: Process large datasets in chunks
async def process_large_document(document: Document) -> ExtractionResult:
    """Process large document in memory-efficient chunks."""
    chunks = self._chunk_document(document, max_size=config.chunk_size)
    
    all_entities = []
    all_relationships = []
    
    for chunk in chunks:
        # Process and save immediately to avoid memory buildup
        entities, relationships = await self._process_chunk(chunk)
        await self._save_chunk_results(entities, relationships)
        
        all_entities.extend(entities)
        all_relationships.extend(relationships)
        
        # Clear chunk data
        del entities, relationships
    
    return ExtractionResult(
        document_id=document.id,
        entities=all_entities,
        relationships=all_relationships
    )
```

## Database Development

### Neo4j Development

```python
# Good: Use parameterized queries
async def find_entities_by_type(self, entity_type: str) -> List[Dict]:
    """Find entities by type using dynamic labels."""
    sanitized_type = self._sanitize_label(entity_type)
    
    # Use dynamic label for better performance
    query = f"""
    MATCH (e:Entity:{sanitized_type})
    RETURN e.id as id, e.name as name, e.properties as properties
    LIMIT $limit
    """
    
    async with self.driver.session() as session:
        result = await session.run(query, limit=100)
        return [dict(record) for record in result]

# Good: Handle transaction failures
async def create_entity_with_retry(self, entity: Entity) -> bool:
    """Create entity with automatic retry on transient failures."""
    for attempt in range(3):
        try:
            async with self.driver.session() as session:
                await session.execute_write(self._create_entity_tx, entity)
                return True
        except neo4j.exceptions.TransientError as e:
            logger.warning(f"Transient error (attempt {attempt + 1}): {e}")
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            logger.error(f"Permanent error creating entity: {e}")
            return False
    
    return False
```

### Supabase Development

```python
# Good: Use proper error handling
async def upsert_domain_type(
    self, 
    domain: str, 
    entity_type: str, 
    confidence: float
) -> bool:
    """Upsert domain entity type with proper error handling."""
    try:
        # Use upsert to handle duplicates gracefully
        result = self.client.table('domain_entity_types').upsert({
            'domain': domain,
            'entity_type': entity_type,
            'confidence_score': confidence,
            'usage_count': 1
        }, on_conflict='domain,entity_type').execute()
        
        if result.data:
            logger.debug(f"Upserted domain type: {domain}.{entity_type}")
            return True
        else:
            logger.warning(f"No data returned from upsert: {domain}.{entity_type}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to upsert domain type {domain}.{entity_type}: {e}")
        return False
```

## Debugging Guidelines

### Logging Strategy

```python
import logging
from rich.logging import RichHandler

# Configure rich logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)

logger = logging.getLogger(__name__)

# Good: Structured logging with context
logger.info(
    f"🧠 Processing document: {document.title} "
    f"({len(document.content)} chars, {document.document_type})"
)

logger.debug(
    f"📊 Extraction stats: {len(entities)} entities, "
    f"{len(relationships)} relationships, "
    f"{processing_time:.2f}s"
)

# Good: Error logging with actionable information
logger.error(
    f"❌ Failed to connect to Neo4j: {e}. "
    f"Check connection settings: {config.neo4j_uri}"
)
```

### Development Tools

```bash
# Debug database state
python -c "
from src.akg.database.neo4j_manager import Neo4jManager
import asyncio

async def debug_neo4j():
    neo4j = Neo4jManager()
    await neo4j.initialize()
    stats = await neo4j.get_graph_stats()
    print(f'Entities: {stats[\"total_entities\"]}')
    print(f'Relationships: {stats[\"total_relationships\"]}')
    await neo4j.close()

asyncio.run(debug_neo4j())
"

# Test specific extraction
python tests/test_extraction_comparison.py

# Validate configuration
python -c "from src.akg.config import config; print('Config loaded successfully')"
```

## Contributing Guidelines

### Pull Request Process

1. **Create Feature Branch**: `git checkout -b feature/description`
2. **Write Tests**: Ensure new functionality is tested
3. **Update Documentation**: Add/update relevant documentation
4. **Run Tests**: `python -m pytest tests/ -v`
5. **Check Style**: `black src/ tests/` and `isort src/ tests/`
6. **Create PR**: With clear description and test results

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] New functionality has tests
- [ ] Documentation is updated
- [ ] Error handling is appropriate
- [ ] Performance impact is considered
- [ ] Database changes include migrations
- [ ] Configuration changes are documented

This development guide provides comprehensive information for contributing to and extending the AKG system.
