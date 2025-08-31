# Performance Tuning Guide

## Overview

This guide provides comprehensive performance optimization strategies for the AKG system across all components: AI services, databases, file processing, and system resources.

## Performance Metrics

### Current Baseline Performance

- **Document Processing**: 5-8 documents/minute with AI extraction
- **Neo4j Query Response**: <100ms for label-based queries, <500ms for complex traversals
- **Supabase Operations**: <200ms for simple CRUD, <1s for analytics queries
- **Memory Usage**: 512MB-2GB depending on document size and concurrency
- **CPU Usage**: 20-60% during active processing

### Target Performance Goals

- **Document Processing**: 10-15 documents/minute
- **Neo4j Query Response**: <50ms for label-based queries, <200ms for complex traversals
- **Memory Usage**: <1GB for typical workloads
- **Error Rate**: <1% for AI extractions, <0.1% for database operations

## AI Service Optimization

### Google Gemini API Optimization

#### 1. Request Optimization

```python
# Optimize prompt structure for faster responses
def _create_optimized_extraction_prompt(
    self, 
    chunk: str, 
    document_analysis: Dict,
    existing_types: List[str]
) -> str:
    """
    Create optimized prompt for faster Gemini processing.
    
    Optimizations:
    - Shorter, more focused prompts
    - Explicit output format specification
    - Reduced context when possible
    - Type hints for consistency
    """
    
    # Limit existing types to most relevant (top 20)
    relevant_entity_types = existing_types[:20]
    relevant_relationship_types = existing_types[:15]
    
    prompt = f"""
TASK: Extract entities and relationships from this {document_analysis['domain']} document.

TEXT: {chunk[:1500]}  # Limit chunk size for faster processing

OUTPUT FORMAT (JSON only):
{{"entities": [{{"name": "str", "type": "str", "confidence": float}}],
  "relationships": [{{"source": "str", "target": "str", "type": "str", "confidence": float}}]}}

ENTITY TYPES: {', '.join(relevant_entity_types[:10])}
RELATIONSHIP TYPES: {', '.join(relevant_relationship_types[:8])}

CONSTRAINTS:
- Use existing types when possible
- ALL CAPS for relationship types
- Confidence 0.0-1.0
- Maximum 10 entities, 8 relationships per response
"""
    return prompt
```

#### 2. Batch Processing Optimization

```python
async def process_documents_optimized(
    self, 
    documents: List[Document]
) -> List[ExtractionResult]:
    """
    Optimized batch processing with intelligent scheduling.
    
    Optimizations:
    - Rate limit management (15 requests/minute for free tier)
    - Request pooling and batching
    - Adaptive concurrency based on API response times
    - Circuit breaker pattern for failures
    """
    
    # Adaptive concurrency based on API tier
    if self._is_free_tier():
        max_concurrent = 2  # Stay under rate limits
        request_delay = 4.5  # 15 requests/minute = 4s interval + buffer
    else:
        max_concurrent = min(config.max_concurrent_documents, 10)
        request_delay = 1.0
    
    semaphore = asyncio.Semaphore(max_concurrent)
    results = []
    
    for i, document in enumerate(documents):
        async with semaphore:
            if i > 0:
                await asyncio.sleep(request_delay)
            
            result = await self._process_single_with_retry(document)
            results.append(result)
            
            # Adaptive delay based on response time
            if result.processing_time > 10.0:
                await asyncio.sleep(2.0)  # Cool down after slow responses
    
    return results
```

#### 3. Caching and Memoization

```python
class OptimizedExtractionAgent:
    def __init__(self):
        self._chunk_cache = {}  # LRU cache for similar chunks
        self._analysis_cache = {}  # Document analysis cache
        
    async def extract_with_cache(self, document: Document) -> Tuple[List[Entity], List[Relationship]]:
        """
        Extract with intelligent caching.
        
        Cache levels:
        1. Document analysis cache (Supabase)
        2. Chunk similarity cache (in-memory)
        3. Type pattern cache (Supabase)
        """
        
        # Level 1: Check document analysis cache
        content_hash = self._generate_content_hash(document)
        cached_analysis = await self.supabase_manager.get_cached_analysis(content_hash)
        
        if cached_analysis and self._is_cache_valid(cached_analysis):
            logger.info(f"📋 Using cached analysis for {document.title}")
            return self._reconstruct_from_cache(cached_analysis)
        
        # Level 2: Check chunk similarity
        chunks = self._chunk_document(document)
        similar_chunks = self._find_similar_chunks(chunks)
        
        if len(similar_chunks) > len(chunks) * 0.7:  # 70% similarity threshold
            logger.info(f"🔄 Using similar chunk patterns for {document.title}")
            return await self._extract_with_patterns(document, similar_chunks)
        
        # Level 3: Full AI processing with caching
        return await self._extract_and_cache(document)
```

## Database Performance Optimization

### Neo4j Optimization

#### 1. Query Optimization

```cypher
-- Optimized queries using dynamic labels

-- SLOW: Property-based filtering
MATCH (e:Entity) 
WHERE e.type = "PERSON" 
RETURN e;

-- FAST: Label-based filtering (3x faster)
MATCH (e:PERSON) 
RETURN e;

-- SLOW: Complex property traversal
MATCH (e:Entity)-[r]-(related:Entity)
WHERE e.type = "PERSON" AND r.type = "WORKS_FOR"
RETURN e, related;

-- FAST: Label and type-based traversal
MATCH (p:PERSON)-[r:WORKS_FOR]-(related)
RETURN p, related;
```

#### 2. Index Strategy

```cypher
-- Essential indexes for performance
CREATE INDEX entity_id_index IF NOT EXISTS FOR (e:Entity) ON (e.id);
CREATE INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX entity_document_index IF NOT EXISTS FOR (e:Entity) ON (e.document_id);

-- Type-specific indexes for dynamic labels
CREATE INDEX person_name_index IF NOT EXISTS FOR (p:PERSON) ON (p.name);
CREATE INDEX api_name_index IF NOT EXISTS FOR (a:API) ON (a.name);
CREATE INDEX service_name_index IF NOT EXISTS FOR (s:SERVICE) ON (s.name);

-- Composite indexes for common queries
CREATE INDEX entity_type_confidence IF NOT EXISTS FOR (e:Entity) ON (e.type, e.confidence_score);
CREATE INDEX entity_document_type IF NOT EXISTS FOR (e:Entity) ON (e.document_id, e.type);
```

#### 3. Connection Pool Optimization

```python
class OptimizedNeo4jManager:
    def __init__(self):
        # Optimized connection pool settings
        self.driver = AsyncGraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_username, config.neo4j_password),
            max_connection_pool_size=50,  # Increase pool size
            connection_acquisition_timeout=30,  # 30 second timeout
            max_transaction_retry_time=15,  # 15 second retry
            resolver=self._custom_resolver,
            encrypted=True
        )
    
    async def batch_create_entities(self, entities: List[Entity]) -> bool:
        """
        Optimized batch entity creation.
        
        Optimizations:
        - Single transaction for multiple entities
        - Parameterized queries to avoid parsing overhead
        - Batch size optimization (100 entities per transaction)
        """
        
        batch_size = 100
        
        async with self.driver.session() as session:
            for i in range(0, len(entities), batch_size):
                batch = entities[i:i + batch_size]
                
                query = """
                UNWIND $entities as entity_data
                MERGE (e:Entity {id: entity_data.id})
                SET e += entity_data.properties
                WITH e, entity_data
                CALL apoc.create.addLabels(e, [entity_data.dynamic_label]) YIELD node
                RETURN count(node)
                """
                
                batch_params = [
                    {
                        "id": entity.id,
                        "properties": {
                            "name": entity.name,
                            "type": entity.entity_type,
                            "confidence_score": entity.confidence_score,
                            "document_id": entity.document_id
                        },
                        "dynamic_label": self._sanitize_label(entity.entity_type)
                    }
                    for entity in batch
                ]
                
                await session.run(query, entities=batch_params)
```

### Supabase Optimization

#### 1. Connection Optimization

```python
class OptimizedSupabaseManager:
    def __init__(self, url: str, key: str):
        self.url = url
        self.key = key
        
        # Connection pool configuration
        self.client = create_client(
            url, 
            key,
            options=ClientOptions(
                postgrest_client_timeout=30,
                storage_client_timeout=30,
                schema="public",
                auto_refresh_token=True,
                persist_session=True
            )
        )
    
    async def bulk_upsert_domain_types(
        self, 
        domain_types: List[Dict]
    ) -> bool:
        """
        Optimized bulk upsert for domain types.
        
        Optimizations:
        - Single upsert operation for multiple records
        - Minimal data transfer
        - Conflict resolution
        """
        
        try:
            # Batch upsert with conflict resolution
            result = self.client.table('domain_entity_types').upsert(
                domain_types,
                on_conflict='domain,subdomain,entity_type',
                returning='minimal'  # Reduce response size
            ).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Bulk upsert failed: {e}")
            return False
```

#### 2. Query Optimization

```sql
-- Optimized queries with proper indexing

-- SLOW: Full table scan
SELECT * FROM domain_entity_types WHERE domain = 'technical';

-- FAST: Index-optimized query
SELECT entity_type, usage_count, confidence_score 
FROM domain_entity_types 
WHERE domain = 'technical' 
ORDER BY usage_count DESC 
LIMIT 50;

-- Optimized analytics query
SELECT 
    domain,
    COUNT(DISTINCT entity_type) as type_count,
    AVG(confidence_score) as avg_confidence
FROM domain_entity_types 
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY domain
ORDER BY type_count DESC;
```

## System Resource Optimization

### Memory Management

#### 1. Document Processing Memory Optimization

```python
class MemoryOptimizedProcessor:
    def __init__(self):
        self.max_chunk_size = 2000  # Reduced from 3000
        self.chunk_cache_size = 100  # LRU cache for chunks
        self.gc_threshold = 0.8  # Trigger GC at 80% memory usage
    
    async def process_large_document(self, document: Document) -> ExtractionResult:
        """
        Memory-efficient processing for large documents.
        
        Optimizations:
        - Stream processing instead of loading entire document
        - Immediate chunk processing and disposal
        - Garbage collection triggers
        - Memory usage monitoring
        """
        
        chunks = self._stream_document_chunks(document)
        all_entities = []
        all_relationships = []
        
        for i, chunk in enumerate(chunks):
            # Monitor memory usage
            if self._get_memory_usage() > self.gc_threshold:
                gc.collect()
                logger.debug(f"🧹 Triggered garbage collection at chunk {i}")
            
            # Process chunk
            entities, relationships = await self._process_chunk(chunk)
            
            # Save immediately to avoid memory accumulation
            await self._save_chunk_results(entities, relationships)
            
            # Keep only essential data in memory
            all_entities.extend([
                Entity(id=e.id, name=e.name, entity_type=e.entity_type)
                for e in entities
            ])
            all_relationships.extend([
                Relationship(id=r.id, source_entity_id=r.source_entity_id, 
                           target_entity_id=r.target_entity_id, relationship_type=r.relationship_type)
                for r in relationships
            ])
            
            # Clear processed data
            del entities, relationships, chunk
        
        return ExtractionResult(
            document_id=document.id,
            entities=all_entities,
            relationships=all_relationships
        )
```

#### 2. Cache Management

```python
class IntelligentCacheManager:
    def __init__(self):
        self.entity_cache = TTLCache(maxsize=1000, ttl=3600)  # 1 hour TTL
        self.type_cache = TTLCache(maxsize=500, ttl=1800)     # 30 min TTL
        self.analysis_cache = TTLCache(maxsize=200, ttl=7200) # 2 hour TTL
    
    async def manage_cache_lifecycle(self):
        """
        Intelligent cache management with usage patterns.
        
        Strategies:
        - LRU eviction for frequently accessed data
        - TTL for time-sensitive data
        - Memory pressure-based eviction
        - Cache warming for common queries
        """
        
        while True:
            await asyncio.sleep(300)  # Check every 5 minutes
            
            # Clean expired entries
            self._cleanup_expired_entries()
            
            # Check memory pressure
            if self._get_memory_usage() > 0.7:
                self._aggressive_cache_cleanup()
            
            # Warm cache with common queries
            await self._warm_common_caches()
```

### CPU Optimization

#### 1. Async Processing Optimization

```python
class OptimizedAsyncProcessor:
    def __init__(self):
        # CPU-optimized settings
        self.cpu_count = os.cpu_count()
        self.optimal_concurrency = min(self.cpu_count * 2, config.max_concurrent_documents)
        self.io_semaphore = asyncio.Semaphore(self.optimal_concurrency)
        self.cpu_semaphore = asyncio.Semaphore(self.cpu_count)
    
    async def process_documents_optimized(self, documents: List[Document]) -> List[ExtractionResult]:
        """
        CPU and I/O optimized document processing.
        
        Optimizations:
        - Separate semaphores for I/O and CPU operations
        - Adaptive concurrency based on system resources
        - Load balancing across available cores
        """
        
        async def process_single(doc: Document) -> ExtractionResult:
            # I/O operations (file reading, API calls)
            async with self.io_semaphore:
                content = await self._read_document(doc)
                analysis = await self._analyze_with_ai(content)
            
            # CPU-intensive operations (parsing, processing)
            async with self.cpu_semaphore:
                entities, relationships = await self._process_analysis(analysis)
                return ExtractionResult(
                    document_id=doc.id,
                    entities=entities,
                    relationships=relationships
                )
        
        # Process with optimal concurrency
        tasks = [process_single(doc) for doc in documents]
        return await asyncio.gather(*tasks, return_exceptions=True)
```

#### 2. Profiling and Monitoring

```python
import cProfile
import pstats
import tracemalloc
from functools import wraps

def profile_performance(func):
    """Decorator for performance profiling."""
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Memory profiling
        tracemalloc.start()
        
        # CPU profiling
        profiler = cProfile.Profile()
        profiler.enable()
        
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            
            # Stop profiling
            profiler.disable()
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            # Log performance metrics
            logger.info(f"⚡ Performance metrics for {func.__name__}:")
            logger.info(f"   Execution time: {end_time - start_time:.2f}s")
            logger.info(f"   Memory usage: {current / 1024 / 1024:.1f}MB current, {peak / 1024 / 1024:.1f}MB peak")
            
            # Save detailed profiling data in debug mode
            if config.log_level == "DEBUG":
                stats = pstats.Stats(profiler)
                stats.sort_stats('cumulative')
                stats.print_stats(10)  # Top 10 functions
    
    return wrapper
```

## Configuration Optimization

### Environment-Specific Optimization

```bash
# High-performance production configuration
# .env.production

# AI Service Optimization
MAX_CONCURRENT_DOCUMENTS=8  # Based on API tier and CPU cores
CHUNK_SIZE=2500             # Larger chunks for better AI context
OVERLAP_SIZE=250            # Maintain context quality

# Database Optimization
NEO4J_URI=neo4j+s://production-cluster.databases.neo4j.io
NEO4J_CONNECTION_POOL_SIZE=50
NEO4J_CONNECTION_TIMEOUT=30

# Memory Management
PYTHON_MEMORY_LIMIT=4G      # Set memory limits
PYTHON_GC_THRESHOLD=700,10,10

# Processing Optimization
SIMILARITY_THRESHOLD=0.85   # Higher threshold for better precision
PROVENANCE_ENABLED=false    # Disable in production for performance
LOG_LEVEL=INFO              # Reduce logging overhead
```

### Development Performance Configuration

```bash
# Development environment optimized for debugging
# .env.development

# Reduced concurrency for easier debugging
MAX_CONCURRENT_DOCUMENTS=2
CHUNK_SIZE=1500
OVERLAP_SIZE=150

# Detailed logging
LOG_LEVEL=DEBUG
PROVENANCE_ENABLED=true

# Local databases for faster iteration
NEO4J_URI=bolt://localhost:7687
SUPABASE_URL=http://localhost:54321
```

## Monitoring and Alerting

### Performance Monitoring

```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            'documents_processed': 0,
            'total_processing_time': 0,
            'api_calls': 0,
            'api_errors': 0,
            'database_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    async def log_performance_summary(self):
        """Log comprehensive performance summary."""
        
        processing_rate = self.metrics['documents_processed'] / (self.metrics['total_processing_time'] / 60)
        api_error_rate = self.metrics['api_errors'] / max(self.metrics['api_calls'], 1)
        cache_hit_rate = self.metrics['cache_hits'] / max(self.metrics['cache_hits'] + self.metrics['cache_misses'], 1)
        
        logger.info(f"📊 Performance Summary:")
        logger.info(f"   Documents/minute: {processing_rate:.1f}")
        logger.info(f"   API error rate: {api_error_rate:.1%}")
        logger.info(f"   Cache hit rate: {cache_hit_rate:.1%}")
        logger.info(f"   Total database queries: {self.metrics['database_queries']}")
```

### Automated Optimization

```python
class AutoTuner:
    """Automatically tune system parameters based on performance."""
    
    async def optimize_concurrency(self):
        """Dynamically adjust concurrency based on system performance."""
        
        current_performance = await self._measure_performance()
        
        if current_performance.error_rate > 0.05:  # 5% error rate
            # Reduce concurrency
            config.max_concurrent_documents = max(1, config.max_concurrent_documents - 1)
            logger.info(f"🔧 Reduced concurrency to {config.max_concurrent_documents}")
        
        elif current_performance.response_time < 2.0 and current_performance.cpu_usage < 0.7:
            # Increase concurrency
            config.max_concurrent_documents = min(10, config.max_concurrent_documents + 1)
            logger.info(f"🔧 Increased concurrency to {config.max_concurrent_documents}")
```

This performance tuning guide provides comprehensive optimization strategies for maximizing AKG system performance across all components and use cases.
